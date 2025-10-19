-- AI Cost Dashboard: Utilization Alert Card (inactive seats)
-- Requires dashboard parameter {{total_seats}} (number). Defaults to 250 if not provided.
WITH params AS (
  SELECT
    COALESCE({{date_range.end}}, DATE '2025-12-31') AS end_date,
    COALESCE({{inactive_window_days}}, 14) AS window_days,
    COALESCE({{total_seats}}, 250) AS total_seats
),
recent_activity AS (
  SELECT DISTINCT user_email
  FROM `ai_usage_analytics.cursor_usage_stats`, params p
  WHERE activity_date BETWEEN DATE_SUB(p.end_date, INTERVAL p.window_days DAY) AND p.end_date
  UNION DISTINCT
  SELECT DISTINCT user_email
  FROM `ai_usage_analytics.claude_code_usage_stats`, params p
  WHERE activity_date BETWEEN DATE_SUB(p.end_date, INTERVAL p.window_days DAY) AND p.end_date
  UNION DISTINCT
  SELECT DISTINCT user_email
  FROM `ai_usage_analytics.claude_ai_usage_stats`, params p
  WHERE activity_date BETWEEN DATE_SUB(p.end_date, INTERVAL p.window_days DAY) AND p.end_date
),
summary AS (
  SELECT
    (SELECT total_seats FROM params) AS total_seats,
    COUNT(*) AS active_users
  FROM recent_activity
)
SELECT
  total_seats,
  active_users,
  GREATEST(total_seats - active_users, 0) AS inactive_users,
  ROUND(active_users / NULLIF(total_seats, 0) * 100, 2) AS utilization_pct
FROM summary;
