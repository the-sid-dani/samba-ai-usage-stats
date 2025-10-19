-- AI Cost Dashboard: Tool Breakdown Pie
WITH params AS (
  SELECT
    COALESCE({{date_range.start}}, DATE '2025-10-01') AS start_date,
    COALESCE({{date_range.end}}, DATE '2025-12-31') AS end_date
)
SELECT
  provider,
  ROUND(SUM(amount_usd), 2) AS total_cost_usd
FROM params p
JOIN `ai_usage_analytics.vw_combined_daily_costs` c
  ON c.cost_date BETWEEN p.start_date AND p.end_date
GROUP BY provider
ORDER BY total_cost_usd DESC;
