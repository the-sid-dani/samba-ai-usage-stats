-- AI Cost Dashboard: Utilization Alert Card (inactive seats)
-- Requires dashboard parameters: {{total_seats}}, {{inactive_window_days}}, {{end_date}}
WITH recent_activity AS (
  SELECT DISTINCT user_email
  FROM `ai_usage_analytics.cursor_usage_stats`
  WHERE activity_date BETWEEN DATE_SUB(CAST({{end_date}} AS DATE), INTERVAL {{inactive_window_days}} DAY)
    AND CAST({{end_date}} AS DATE)

  UNION DISTINCT

  SELECT DISTINCT user_email
  FROM `ai_usage_analytics.claude_code_usage_stats`
  WHERE activity_date BETWEEN DATE_SUB(CAST({{end_date}} AS DATE), INTERVAL {{inactive_window_days}} DAY)
    AND CAST({{end_date}} AS DATE)

  UNION DISTINCT

  SELECT DISTINCT user_email
  FROM `ai_usage_analytics.claude_ai_usage_stats`
  WHERE activity_date BETWEEN DATE_SUB(CAST({{end_date}} AS DATE), INTERVAL {{inactive_window_days}} DAY)
    AND CAST({{end_date}} AS DATE)
),
summary AS (
  SELECT
    {{total_seats}} AS total_seats,
    COUNT(*) AS active_users
  FROM recent_activity
)
SELECT
  total_seats,
  active_users,
  GREATEST(total_seats - active_users, 0) AS inactive_users,
  ROUND(active_users / NULLIF(total_seats, 0) * 100, 2) AS utilization_pct
FROM summary;
