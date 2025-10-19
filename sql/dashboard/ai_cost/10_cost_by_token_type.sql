-- AI Cost Dashboard: Cost by Token Type (weekly stacked)
WITH params AS (
  SELECT
    COALESCE({{date_range.start}}, DATE '2025-10-01') AS start_date,
    COALESCE({{date_range.end}}, DATE '2025-12-31') AS end_date
)
SELECT
  DATE_TRUNC(c.activity_date, WEEK) AS week_start,
  CASE
    WHEN c.token_type = 'uncached_input_tokens' THEN 'Input'
    WHEN c.token_type = 'output_tokens' THEN 'Output'
    WHEN c.token_type = 'cache_read_input_tokens' THEN 'Cache Read'
    WHEN c.token_type LIKE 'cache_creation%' THEN 'Cache Write'
    ELSE 'Other'
  END AS token_category,
  ROUND(SUM(c.amount_usd), 2) AS token_cost_usd
FROM params p
JOIN `ai_usage_analytics.claude_cost_report` c
  ON c.activity_date BETWEEN p.start_date AND p.end_date
WHERE c.cost_type = 'tokens'
GROUP BY week_start, token_category
ORDER BY week_start;
