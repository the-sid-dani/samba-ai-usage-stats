-- AI Cost Dashboard KPI: Variance vs Budget (percentage + absolute)
-- Expects a Metabase number parameter {{quarter_budget_usd}} (default 73000)
WITH totals AS (
  SELECT SUM(amount_usd) AS total_cost_usd
  FROM `ai_usage_analytics.vw_combined_daily_costs`
  WHERE cost_date >= CAST({{start_date}} AS DATE)
    AND cost_date <= CAST({{end_date}} AS DATE)
)
SELECT
  ROUND(t.total_cost_usd, 2) AS total_cost_usd,
  {{quarter_budget_usd}} AS budget_usd,
  ROUND(t.total_cost_usd - {{quarter_budget_usd}}, 2) AS variance_usd,
  ROUND((t.total_cost_usd - {{quarter_budget_usd}}) / NULLIF({{quarter_budget_usd}}, 0) * 100, 2) AS variance_pct
FROM totals t;
