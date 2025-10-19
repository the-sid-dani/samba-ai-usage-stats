-- AI Cost Dashboard KPI: Variance vs Budget (percentage + absolute)
-- Expects a Metabase number parameter {{quarter_budget_usd}} (default 73000)
WITH params AS (
  SELECT
    COALESCE({{date_range.start}}, DATE '2025-10-01') AS start_date,
    COALESCE({{date_range.end}}, DATE '2025-12-31') AS end_date,
    COALESCE({{quarter_budget_usd}}, 73000) AS budget_usd
),
totals AS (
  SELECT SUM(amount_usd) AS total_cost_usd
  FROM params p
  JOIN `ai_usage_analytics.vw_combined_daily_costs` c
    ON c.cost_date BETWEEN p.start_date AND p.end_date
)
SELECT
  ROUND(t.total_cost_usd, 2) AS total_cost_usd,
  ROUND(p.budget_usd, 2) AS budget_usd,
  ROUND(t.total_cost_usd - p.budget_usd, 2) AS variance_usd,
  ROUND((t.total_cost_usd - p.budget_usd) / NULLIF(p.budget_usd, 0) * 100, 2) AS variance_pct
FROM totals t
JOIN params p ON 1=1;
