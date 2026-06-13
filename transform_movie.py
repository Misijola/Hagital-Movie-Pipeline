"""
transform_movie.py
------------------
Loads movie_data.csv (from extract step) and:
  1. Fetches genre mapping from TMDB and maps genres to movies
  2. Cleans and enriches movie data (release year, rating category, popularity tier)
  3. Simulates 150 realistic users
  4. Simulates 3000 watch sessions with realistic viewing patterns
  5. Saves three clean output files:
       - movies_clean.csv
       - users.csv
       - watch_sessions.csv
"""

import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests
from config import TMDB_API_KEY

# Fix random seed so results are reproducible every run
random.seed(42)
np.random.seed(42)

BASE_URL = "https://api.themoviedb.org/3"


# ──────────────────────────────────────────────
# STEP 1: Load raw movie data
# ──────────────────────────────────────────────
def load_movies():
    df = pd.read_csv("movie_data.csv")
    print(f"[LOAD] {len(df)} rows loaded from movie_data.csv")
    print(f"[LOAD] Columns found: {list(df.columns)}")
    return df


# ──────────────────────────────────────────────
# STEP 2: Fetch genre mapping from TMDB
# Returns a dict: {genre_id: genre_name}
# Example: {28: 'Action', 35: 'Comedy'}
# ──────────────────────────────────────────────
def fetch_genre_map():
    url = f"{BASE_URL}/genre/movie/list"
    params = {"api_key": TMDB_API_KEY, "language": "en-US"}
    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f"[WARNING] Could not fetch genres: {response.status_code}")
        return {}

    genres = response.json().get("genres", [])
    genre_map = {g["id"]: g["name"] for g in genres}
    print(f"[OK] Fetched {len(genre_map)} genres from TMDB")
    return genre_map


# ──────────────────────────────────────────────
# STEP 3: Clean and enrich movie data
# ──────────────────────────────────────────────
def clean_movies(df, genre_map):

    # Rename 'id' to 'movie_id' for clarity in the database
    df = df.rename(columns={"id": "movie_id"})

    # Drop rows where title or movie_id is missing — unusable records
    df = df.dropna(subset=["movie_id", "title"])

    # Remove duplicate movies (same movie appearing in multiple categories)
    # Keep the first occurrence — e.g. a movie in both 'popular' and 'top_rated'
    df = df.drop_duplicates(subset=["movie_id"])

    # Extract release year from release_date (e.g. "2024-03-15" -> 2024)
    df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")
    df["release_year"] = df["release_date"].dt.year.fillna(0).astype(int)

    # ── Genre mapping ──
    # TMDB genre_ids is a list stored as a string in CSV e.g. "[28, 12, 878]"
    # We parse it and take the first genre as the primary genre
    if "genre_ids" in df.columns:
        def get_primary_genre(genre_ids_raw):
            try:
                # Convert string "[28, 12]" to actual Python list
                ids = eval(str(genre_ids_raw))
                if ids and isinstance(ids, list):
                    return genre_map.get(ids[0], "Other")
            except:
                pass
            return "Other"

        df["genre"] = df["genre_ids"].apply(get_primary_genre)
    else:
        # genre_ids not in CSV — assign genre based on TMDB category
        # This is a fallback using known popular genre patterns
        category_genre_map = {
            "popular":    "Action",
            "top_rated":  "Drama",
            "now_playing": "Thriller",
            "upcoming":   "Adventure"
        }
        df["genre"] = df["category"].map(category_genre_map).fillna("Other")
        print("[INFO] genre_ids not found in CSV — genre assigned from category.")

    # ── Rating category ──
    # Bucket vote_average into human-readable quality tiers
    def rate_category(score):
        if score >= 8.0:
            return "Excellent"
        elif score >= 6.5:
            return "Good"
        elif score >= 5.0:
            return "Average"
        else:
            return "Poor"

    df["rating_category"] = df["vote_average"].apply(rate_category)

    # ── Popularity tier ──
    # Bucket popularity score into High / Medium / Low
    p33 = df["popularity"].quantile(0.33)
    p66 = df["popularity"].quantile(0.66)

    def popularity_tier(score):
        if score >= p66:
            return "High"
        elif score >= p33:
            return "Medium"
        else:
            return "Low"

    df["popularity_tier"] = df["popularity"].apply(popularity_tier)

    # Keep only columns we need for the database
    columns_to_keep = [
        "movie_id", "title", "genre", "release_year",
        "vote_average", "vote_count", "popularity",
        "popularity_tier", "rating_category",
        "original_language", "category"
    ]
    # Only keep columns that actually exist in the dataframe
    columns_to_keep = [c for c in columns_to_keep if c in df.columns]
    df = df[columns_to_keep]

    print(f"[CLEAN] {len(df)} unique movies after cleaning")
    return df


# ──────────────────────────────────────────────
# STEP 4: Simulate 150 users
# ──────────────────────────────────────────────
def simulate_users():
    age_groups = ["18-24", "25-34", "35-44", "45-54", "55+"]
    regions    = ["Lagos", "Abuja", "London", "New York", "Nairobi",
                  "Dubai", "Toronto", "Accra", "Cape Town", "Paris"]

    users = []
    for i in range(1, 151):
        users.append({
            "user_id":   i,
            "username":  f"user_{i:03d}",          # e.g. user_001
            "age_group": random.choice(age_groups),
            "region":    random.choice(regions),
        })

    df_users = pd.DataFrame(users)
    print(f"[SIM] {len(df_users)} users simulated")
    return df_users


# ──────────────────────────────────────────────
# STEP 5: Simulate 3000 watch sessions
# ──────────────────────────────────────────────
def simulate_watch_sessions(df_movies, df_users):
    """
    Creates 3000 realistic watch session records.

    Key design decisions:
    - Sessions spread across the last 90 days
    - Evening hours (18:00-23:00) are most common — mirrors real streaming behaviour
    - Higher rated movies have higher completion rates
    - Watch duration is a random fraction of a typical 2hr movie
    """

    movie_ids = df_movies["movie_id"].tolist()
    user_ids  = df_users["user_id"].tolist()

    # Build a quick lookup: movie_id -> vote_average
    # Used to make completion probability correlate with rating
    rating_lookup = df_movies.set_index("movie_id")["vote_average"].to_dict()

    # Hour weights — evening hours are most popular for streaming
    # Hours 0-23, with 19:00-22:00 getting the most weight
    hour_weights = [
        1, 1, 1, 1, 1, 1,    # 00-05 (late night — low)
        2, 3, 3, 3, 3, 3,    # 06-11 (morning — moderate)
        4, 4, 4, 4, 5, 5,    # 12-17 (afternoon — building up)
        8, 10, 10, 9, 7, 4   # 18-23 (evening — peak)
    ]

    base_date = datetime.now()
    sessions  = []

    for session_id in range(1, 3001):
        movie_id = random.choice(movie_ids)
        user_id  = random.choice(user_ids)

        # Random date within last 90 days
        days_ago = random.randint(0, 90)
        hour     = random.choices(range(24), weights=hour_weights, k=1)[0]
        minute   = random.randint(0, 59)
        watched_at = base_date - timedelta(days=days_ago, hours=hour, minutes=minute)

        # Watch duration: between 20 and 150 minutes
        watch_duration = random.randint(20, 150)

        # Completion: higher-rated movies more likely to be finished
        rating = rating_lookup.get(movie_id, 6.0)
        completion_probability = min(0.9, rating / 10.0 + 0.2)
        completed = random.random() < completion_probability

        sessions.append({
            "session_id":         session_id,
            "user_id":            user_id,
            "movie_id":           movie_id,
            "watched_at":         watched_at.strftime("%Y-%m-%d %H:%M:%S"),
            "watch_duration_mins": watch_duration,
            "completed":          completed,
            "watch_hour":         hour,          # 0-23 (for time-of-day analysis)
            "watch_day":          watched_at.strftime("%A"),   # Monday, Tuesday...
            "watch_month":        watched_at.strftime("%B"),   # January, February...
        })

    df_sessions = pd.DataFrame(sessions)
    print(f"[SIM] {len(df_sessions)} watch sessions simulated")
    return df_sessions


# ──────────────────────────────────────────────
# STEP 6: Validation summary
# ──────────────────────────────────────────────
def print_summary(df_movies, df_users, df_sessions):
    print("\n─── Transform Summary ───")
    print(f"Movies    : {len(df_movies)} rows | Columns: {list(df_movies.columns)}")
    print(f"Users     : {len(df_users)} rows")
    print(f"Sessions  : {len(df_sessions)} rows")
    print(f"\nGenre breakdown:\n{df_movies['genre'].value_counts()}")
    print(f"\nRating categories:\n{df_movies['rating_category'].value_counts()}")
    print(f"\nTop 5 most popular movies:")
    top5 = df_movies.nlargest(5, "popularity")[["title", "genre", "vote_average", "popularity"]]
    print(top5.to_string(index=False))
    print("─────────────────────────\n")


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    print("=== TRANSFORM: Movie Pipeline ===\n")

    # 1. Load raw data
    df_movies = load_movies()

    # 2. Fetch genre mapping from TMDB
    genre_map = fetch_genre_map()

    # 3. Clean and enrich movies
    df_movies = clean_movies(df_movies, genre_map)

    # 4. Simulate users
    df_users = simulate_users()

    # 5. Simulate watch sessions
    df_sessions = simulate_watch_sessions(df_movies, df_users)

    # 6. Print summary
    print_summary(df_movies, df_users, df_sessions)

    # 7. Save all three to CSV
    df_movies.to_csv("movies_clean.csv", index=False)
    df_users.to_csv("users.csv", index=False)
    df_sessions.to_csv("watch_sessions.csv", index=False)

    print("[SAVED] movies_clean.csv")
    print("[SAVED] users.csv")
    print("[SAVED] watch_sessions.csv")
    print("\n=== TRANSFORM complete ===")


if __name__ == "__main__":
    main()