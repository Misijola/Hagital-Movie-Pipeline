import pandas as pd
import requests
from config import TMDB_READ_TOKEN

BASE_URL = "https://api.themoviedb.org/3"
HEADERS = {
    "Authorization": f"Bearer {TMDB_READ_TOKEN}",
    "accept": "application/json"
}

CATEGORIES = ["popular", "top_rated", "now_playing", "upcoming"]


def fetch_movies(category, pages=5):
    """Fetch movies for a given category across multiple pages."""
    rows = []
    for page in range(1, pages + 1):
        url = f"{BASE_URL}/movie/{category}"
        response = requests.get(url, headers=HEADERS, params={"page": page})
        response.raise_for_status()
        results = response.json().get("results", [])
        for movie in results:
            rows.append({
                "category": category,
                "id": movie.get("id"),
                "title": movie.get("title"),
                "release_date": movie.get("release_date"),
                "popularity": movie.get("popularity"),
                "vote_average": movie.get("vote_average"),
                "vote_count": movie.get("vote_count"),
                "overview": movie.get("overview"),
                "original_language": movie.get("original_language"),
            })
    return rows


def fetch_all_movies():
    """Fetch movies across all categories and return a DataFrame."""
    all_data = []
    for category in CATEGORIES:
        print(f"Fetching {category} movies...")
        all_data.extend(fetch_movies(category))

    df = pd.DataFrame(all_data)
    df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")
    df = df.drop_duplicates(subset=["id", "category"])
    return df


if __name__ == "__main__":
    df = fetch_all_movies()
    print(df.head(20))
    print(f"\nTotal rows fetched: {len(df)}")
    df.to_csv("movie_data.csv", index=False)
    print("Saved to movie_data.csv")
