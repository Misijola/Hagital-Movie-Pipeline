# Movie Streaming Platform Analytics

**Hagital Consulting Data Engineering Bootcamp — Group 5 Project**  

## Overview
An end-to-end ETL pipeline that fetches real movie data from the TMDB API,
simulates user watch behaviour, loads everything into PostgreSQL, and
visualizes insights on a Grafana dashboard.

## Pipeline Structure
extract_movie.py--> transform_movie.py--> load_movie.py

## Tech Stack
- **Python** (requests, pandas, psycopg2, SQLAlchemy)
- **TMDB API** — live movie metadata
- **PostgreSQL** — 3 tables: movies, users, watch_sessions
- **Grafana** — 3 dashboard panels
- **Excel** — movie_output.xlsx (3 sheets)

## Database Schema
| Table | Rows | Description |
|---|---|---|
| movies | 332 | TMDB movie metadata |
| users | 150 | Simulated streaming users |
| watch_sessions | 3000 | Simulated viewing logs |

## Grafana Dashboard Panels
1. Top 10 Trending Movies (horizontal bar chart)
2. Genre Popularity (pie chart)
3. Viewing Patterns by Hour of Day (bar chart)

## Key Insights
- Action is the most watched genre (30%)
- Peak viewing hour is 19:00 with 329 sessions
- Scary Movie ranked #1 by watch count