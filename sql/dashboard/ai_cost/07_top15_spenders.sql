-- AI Cost Dashboard: Top 15 Users by Spend
SELECT
  user_email,
  ROUND(SUM(amount_usd), 2) AS total_cost_usd,
  {{alert_threshold_usd}} AS alert_threshold_usd
FROM `ai_usage_analytics.vw_combined_daily_costs`
WHERE cost_date >= CAST({{start_date}} AS DATE)
  AND cost_date <= CAST({{end_date}} AS DATE)
  AND user_email IS NOT NULL
GROUP BY user_email
ORDER BY total_cost_usd DESC
LIMIT 15;
