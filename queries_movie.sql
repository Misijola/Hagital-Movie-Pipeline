-- ============================================================
-- queries_movie.sql
-- Movie Streaming Platform Analytics — SQL Query Scripts
-- Database: movie_db
-- ============================================================


-- ── 1. Total records in each table ──
SELECT 'movies'        AS table_name, COUNT(*) AS total FROM movies
UNION ALL
SELECT 'users',                        COUNT(*) FROM users
UNION ALL
SELECT 'watch_sessions',               COUNT(*) FROM watch_sessions;


-- ── 2. Top 10 most watched movies ──
SELECT
    m.title,
    m.genre,
    m.vote_average,
    COUNT(w.session_id)          AS total_watches,
    ROUND(AVG(w.watch_duration_mins), 1) AS avg_watch_duration
FROM watch_sessions w
JOIN movies m ON w.movie_id = m.movie_id
GROUP BY m.title, m.genre, m.vote_average
ORDER BY total_watches DESC
LIMIT 10;


-- ── 3. Genre popularity — total watches per genre ──
SELECT
    m.genre,
    COUNT(w.session_id)  AS total_watches,
    ROUND(AVG(m.vote_average), 2) AS avg_rating
FROM watch_sessions w
JOIN movies m ON w.movie_id = m.movie_id
GROUP BY m.genre
ORDER BY total_watches DESC;


-- ── 4. Viewing patterns by time of day ──
-- Buckets: Morning(6-11), Afternoon(12-17), Evening(18-22), Night(23-5)
SELECT
    CASE
        WHEN watch_hour BETWEEN 6  AND 11 THEN 'Morning'
        WHEN watch_hour BETWEEN 12 AND 17 THEN 'Afternoon'
        WHEN watch_hour BETWEEN 18 AND 22 THEN 'Evening'
        ELSE 'Night'
    END                        AS time_of_day,
    COUNT(session_id)          AS total_sessions,
    ROUND(COUNT(session_id) * 100.0 / SUM(COUNT(session_id)) OVER(), 1) AS pct
FROM watch_sessions
GROUP BY time_of_day
ORDER BY total_sessions DESC;


-- ── 5. Completion rate per genre (window function) ──
SELECT
    m.genre,
    COUNT(w.session_id)                                   AS total_watches,
    SUM(CASE WHEN w.completed THEN 1 ELSE 0 END)          AS completed_count,
    ROUND(
        SUM(CASE WHEN w.completed THEN 1 ELSE 0 END) * 100.0
        / COUNT(w.session_id), 1
    )                                                     AS completion_pct
FROM watch_sessions w
JOIN movies m ON w.movie_id = m.movie_id
GROUP BY m.genre
ORDER BY completion_pct DESC;


-- ── 6. Top 5 users by total watch time ──
SELECT
    u.username,
    u.region,
    u.age_group,
    COUNT(w.session_id)            AS sessions,
    SUM(w.watch_duration_mins)     AS total_mins_watched
FROM watch_sessions w
JOIN users u ON w.user_id = u.user_id
GROUP BY u.username, u.region, u.age_group
ORDER BY total_mins_watched DESC
LIMIT 5;


-- ── 7. Monthly watch trend ──
SELECT
    watch_month,
    COUNT(session_id)          AS total_sessions,
    SUM(watch_duration_mins)   AS total_mins
FROM watch_sessions
GROUP BY watch_month
ORDER BY total_sessions DESC;


-- ── 8. Window function — rank movies by watches within each genre ──
SELECT
    genre,
    title,
    total_watches,
    RANK() OVER (PARTITION BY genre ORDER BY total_watches DESC) AS rank_in_genre
FROM (
    SELECT
        m.genre,
        m.title,
        COUNT(w.session_id) AS total_watches
    FROM watch_sessions w
    JOIN movies m ON w.movie_id = m.movie_id
    GROUP BY m.genre, m.title
) ranked
ORDER BY genre, rank_in_genre
LIMIT 20;


-- ── 9. Grafana panel 1 — Top 10 trending movies (by watch count) ──
SELECT
    m.title        AS "Movie",
    m.genre        AS "Genre",
    m.vote_average AS "Rating",
    COUNT(w.session_id) AS "Watch Count"
FROM watch_sessions w
JOIN movies m ON w.movie_id = m.movie_id
GROUP BY m.title, m.genre, m.vote_average
ORDER BY "Watch Count" DESC
LIMIT 10;


-- ── 10. Grafana panel 2 — Genre popularity (watch count per genre) ──
SELECT
    m.genre        AS "Genre",
    COUNT(w.session_id) AS "Total Watches"
FROM watch_sessions w
JOIN movies m ON w.movie_id = m.movie_id
GROUP BY m.genre
ORDER BY "Total Watches" DESC;


-- ── 11. Grafana panel 3 — Viewing patterns by hour ──
SELECT
    watch_hour     AS "Hour",
    COUNT(session_id) AS "Sessions"
FROM watch_sessions
GROUP BY watch_hour
ORDER BY watch_hour;