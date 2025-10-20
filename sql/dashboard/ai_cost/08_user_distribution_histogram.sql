-- AI Cost Dashboard: User Distribution Histogram
WITH user_totals AS (
  SELECT
    user_email,
    SUM(amount_usd) AS total_cost_usd
  FROM `ai_usage_analytics.vw_combined_daily_costs`
  WHERE cost_date >= CAST({{start_date}} AS DATE)
    AND cost_date <= CAST({{end_date}} AS DATE)
    AND user_email IS NOT NULL
  GROUP BY user_email
)
SELECT
  CASE
    WHEN total_cost_usd < 100 THEN '$0-100'
    WHEN total_cost_usd < 300 THEN '$100-300'
    WHEN total_cost_usd < 500 THEN '$300-500'
    WHEN total_cost_usd < 1000 THEN '$500-1000'
    ELSE '$1000+'
  END AS cost_range,
  COUNT(*) AS user_count
FROM user_totals
GROUP BY cost_range
ORDER BY MIN(total_cost_usd);
