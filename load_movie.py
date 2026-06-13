"""
load_movie.py
-------------
Loads the three cleaned CSVs into PostgreSQL (movie_db) and
exports all data to movie_output.xlsx with three sheets.

Tables created:
  - movies       (from movies_clean.csv)
  - users        (from users.csv)
  - watch_sessions (from watch_sessions.csv)
"""

import pandas as pd
import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine

# ── Database connection settings ──
DB_NAME = "movie_db"
DB_USER = "postgres"
DB_PASS = "yourpassword"   # change to your PostgreSQL password
DB_HOST = "localhost"
DB_PORT = "5432"

# SQLAlchemy engine for pandas to_sql
ENGINE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def load_csvs():
    """Load all three cleaned CSVs into DataFrames."""
    df_movies   = pd.read_csv("movies_clean.csv")
    df_users    = pd.read_csv("users.csv")
    df_sessions = pd.read_csv("watch_sessions.csv")

    print(f"[LOAD] movies_clean.csv   — {len(df_movies)} rows")
    print(f"[LOAD] users.csv          — {len(df_users)} rows")
    print(f"[LOAD] watch_sessions.csv — {len(df_sessions)} rows")

    return df_movies, df_users, df_sessions


def create_tables(conn):
    """
    Create the three tables in movie_db.
    DROP IF EXISTS ensures a clean reload every time the script runs.
    """
    cur = conn.cursor()

    cur.execute("""
        DROP TABLE IF EXISTS watch_sessions;
        DROP TABLE IF EXISTS movies;
        DROP TABLE IF EXISTS users;
    """)

    # movies table — one row per unique movie from TMDB
    cur.execute("""
        CREATE TABLE movies (
            movie_id          INTEGER PRIMARY KEY,
            title             TEXT NOT NULL,
            genre             VARCHAR(50),
            release_year      INTEGER,
            vote_average      NUMERIC(4,2),
            vote_count        INTEGER,
            popularity        NUMERIC(10,4),
            popularity_tier   VARCHAR(10),
            rating_category   VARCHAR(10),
            original_language VARCHAR(10),
            category          VARCHAR(20)
        );
    """)

    # users table — simulated streaming platform users
    cur.execute("""
        CREATE TABLE users (
            user_id    INTEGER PRIMARY KEY,
            username   VARCHAR(50),
            age_group  VARCHAR(10),
            region     VARCHAR(50)
        );
    """)

    # watch_sessions table — links users to movies with timestamps
    cur.execute("""
        CREATE TABLE watch_sessions (
            session_id          INTEGER PRIMARY KEY,
            user_id             INTEGER REFERENCES users(user_id),
            movie_id            INTEGER REFERENCES movies(movie_id),
            watched_at          TIMESTAMP,
            watch_duration_mins INTEGER,
            completed           BOOLEAN,
            watch_hour          INTEGER,
            watch_day           VARCHAR(10),
            watch_month         VARCHAR(10)
        );
    """)

    conn.commit()
    cur.close()
    print("[OK] Tables created: movies, users, watch_sessions")


def insert_data(df_movies, df_users, df_sessions, engine):
    """
    Use pandas to_sql to bulk-insert all three DataFrames.
    if_exists='append' because the tables are already created above.
    """
    df_movies.to_sql("movies",         engine, if_exists="append", index=False)
    df_users.to_sql("users",           engine, if_exists="append", index=False)
    df_sessions.to_sql("watch_sessions", engine, if_exists="append", index=False)

    print("[OK] Data inserted into all three tables")


def export_excel(df_movies, df_users, df_sessions):
    """Export all three tables to one Excel file with separate sheets."""
    output_file = "movie_output.xlsx"

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        df_movies.to_excel(writer,   sheet_name="Movies",         index=False)
        df_users.to_excel(writer,    sheet_name="Users",          index=False)
        df_sessions.to_excel(writer, sheet_name="Watch_Sessions", index=False)

    print(f"[SAVED] {output_file} — 3 sheets exported")


def main():
    print("=== LOAD: Movie Pipeline ===\n")

    # 1. Load CSVs
    df_movies, df_users, df_sessions = load_csvs()

    # 2. Connect to PostgreSQL and create tables
    conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER,
        password=DB_PASS, host=DB_HOST, port=DB_PORT
    )
    create_tables(conn)
    conn.close()

    # 3. Insert data using SQLAlchemy engine
    engine = create_engine(ENGINE_URL)
    insert_data(df_movies, df_users, df_sessions, engine)

    # 4. Export to Excel
    export_excel(df_movies, df_users, df_sessions)

    print("\n=== LOAD complete ===")


if __name__ == "__main__":
    main()