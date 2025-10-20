-- AI Cost Dashboard KPI: Cost Per Active User
WITH user_costs AS (
  SELECT
    user_email,
    SUM(amount_usd) AS total_cost
  FROM `ai_usage_analytics.vw_combined_daily_costs`
  WHERE cost_date >= CAST({{start_date}} AS DATE)
    AND cost_date <= CAST({{end_date}} AS DATE)
    AND user_email IS NOT NULL
  GROUP BY user_email
)
SELECT
  ROUND(SUM(total_cost) / NULLIF(COUNT(DISTINCT user_email), 0), 2) AS cost_per_user_usd,
  COUNT(DISTINCT user_email) AS active_users
FROM user_costs;
