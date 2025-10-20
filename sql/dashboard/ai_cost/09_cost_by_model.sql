-- AI Cost Dashboard: Cost by Model (weekly stacked)
SELECT
  DATE_TRUNC(cost_date, WEEK) AS week_start,
  COALESCE(model, 'Unknown') AS model,
  ROUND(SUM(amount_usd), 2) AS model_cost_usd
FROM `ai_usage_analytics.vw_combined_daily_costs`
WHERE cost_date >= CAST({{start_date}} AS DATE)
  AND cost_date <= CAST({{end_date}} AS DATE)
  AND model IS NOT NULL
GROUP BY week_start, model
ORDER BY week_start, model_cost_usd DESC;
