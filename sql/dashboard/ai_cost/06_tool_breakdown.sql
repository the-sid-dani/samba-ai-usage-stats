-- AI Cost Dashboard: Tool Breakdown Pie
SELECT
  provider,
  ROUND(SUM(amount_usd), 2) AS total_cost_usd
FROM `ai_usage_analytics.vw_combined_daily_costs`
WHERE cost_date >= CAST({{start_date}} AS DATE)
  AND cost_date <= CAST({{end_date}} AS DATE)
GROUP BY provider
ORDER BY total_cost_usd DESC;
