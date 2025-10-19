-- AI Cost Dashboard KPI: Cost Per Active User
WITH params AS (
  SELECT
    COALESCE({{date_range.start}}, DATE '2025-10-01') AS start_date,
    COALESCE({{date_range.end}}, DATE '2025-12-31') AS end_date
),
user_costs AS (
  SELECT
    user_email,
    SUM(amount_usd) AS total_cost
  FROM params p
  JOIN `ai_usage_analytics.vw_combined_daily_costs` c
    ON c.cost_date BETWEEN p.start_date AND p.end_date
  WHERE user_email IS NOT NULL
  GROUP BY user_email
)
SELECT
  ROUND(SUM(total_cost) / NULLIF(COUNT(DISTINCT user_email), 0), 2) AS cost_per_user_usd,
  COUNT(DISTINCT user_email) AS active_users
FROM user_costs;
