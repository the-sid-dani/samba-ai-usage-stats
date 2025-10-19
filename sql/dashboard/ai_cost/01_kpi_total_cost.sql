-- AI Cost Dashboard KPI: Q4 Total Cost (returns overall + provider breakdown)
WITH params AS (
  SELECT
    COALESCE({{date_range.start}}, DATE '2025-10-01') AS start_date,
    COALESCE({{date_range.end}}, DATE '2025-12-31') AS end_date
),
filtered AS (
  SELECT c.*
  FROM params p
  JOIN `ai_usage_analytics.vw_combined_daily_costs` c
    ON c.cost_date BETWEEN p.start_date AND p.end_date
)
SELECT
  ROUND(SUM(amount_usd), 2) AS total_cost_usd,
  ROUND(SUM(IF(provider = 'claude_api', amount_usd, 0)), 2) AS claude_api_cost_usd,
  ROUND(SUM(IF(provider = 'claude_code', amount_usd, 0)), 2) AS claude_code_cost_usd,
  ROUND(SUM(IF(provider = 'cursor', amount_usd, 0)), 2) AS cursor_cost_usd
FROM filtered;
