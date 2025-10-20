-- AI Cost Dashboard: Daily Spend Trend with Budget Reference
SELECT
  cost_date,
  ROUND(SUM(amount_usd), 2) AS total_cost_usd,
  {{daily_budget_usd}} AS budget_reference_usd,
  ROUND((SUM(amount_usd) - {{daily_budget_usd}}) / NULLIF({{daily_budget_usd}}, 0) * 100, 2) AS pct_vs_budget
FROM `ai_usage_analytics.vw_combined_daily_costs`
WHERE cost_date >= CAST({{start_date}} AS DATE)
  AND cost_date <= CAST({{end_date}} AS DATE)
GROUP BY cost_date
ORDER BY cost_date;
