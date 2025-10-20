-- AI Cost Dashboard KPI: Q4 Total Cost (returns overall + provider breakdown)
SELECT
  ROUND(SUM(amount_usd), 2) AS total_cost_usd,
  ROUND(SUM(IF(provider = 'claude_api', amount_usd, 0)), 2) AS claude_api_cost_usd,
  ROUND(SUM(IF(provider = 'claude_code', amount_usd, 0)), 2) AS claude_code_cost_usd,
  ROUND(SUM(IF(provider = 'cursor', amount_usd, 0)), 2) AS cursor_cost_usd
FROM `ai_usage_analytics.vw_combined_daily_costs`
WHERE cost_date >= CAST({{start_date}} AS DATE)
  AND cost_date <= CAST({{end_date}} AS DATE);
