-- AI Cost Dashboard: Cost by Model (weekly stacked)
WITH params AS (
  SELECT
    COALESCE({{date_range.start}}, DATE '2025-10-01') AS start_date,
    COALESCE({{date_range.end}}, DATE '2025-12-31') AS end_date
)
SELECT
  DATE_TRUNC(c.activity_date, WEEK) AS week_start,
  COALESCE(c.model, 'Unknown') AS model,
  ROUND(SUM(c.amount_usd), 2) AS model_cost_usd
FROM params p
JOIN `ai_usage_analytics.claude_cost_report` c
  ON c.activity_date BETWEEN p.start_date AND p.end_date
WHERE c.model IS NOT NULL
GROUP BY week_start, model
ORDER BY week_start, model_cost_usd DESC;
