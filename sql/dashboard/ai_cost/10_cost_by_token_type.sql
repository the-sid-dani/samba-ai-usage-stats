-- AI Cost Dashboard: Cost by Token Type (weekly stacked)
SELECT
  DATE_TRUNC(cost_date, WEEK) AS week_start,
  CASE
    WHEN description LIKE '%Cache Hit%' THEN 'Cache Read'
    WHEN description LIKE '%Cache Write%' THEN 'Cache Write'
    WHEN description LIKE '%Output Tokens%' THEN 'Output'
    WHEN description LIKE '%Input Tokens%' AND description NOT LIKE '%Cache%' THEN 'Input'
    ELSE 'Other'
  END AS token_category,
  ROUND(SUM(amount_usd), 2) AS token_cost_usd
FROM `ai_usage_analytics.vw_combined_daily_costs`
WHERE cost_date >= CAST({{start_date}} AS DATE)
  AND cost_date <= CAST({{end_date}} AS DATE)
  AND cost_category = 'tokens'
GROUP BY week_start, token_category
ORDER BY week_start;
