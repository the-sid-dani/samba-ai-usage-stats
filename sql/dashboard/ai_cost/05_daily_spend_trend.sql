-- AI Cost Dashboard: Daily Spend Trend with Budget Reference
WITH params AS (
  SELECT
    COALESCE({{date_range.start}}, DATE '2025-10-01') AS start_date,
    COALESCE({{date_range.end}}, DATE '2025-12-31') AS end_date,
    COALESCE({{daily_budget_usd}}, 793.48) AS daily_budget_usd
),
daily_totals AS (
  SELECT
    c.cost_date,
    SUM(c.amount_usd) AS total_cost_usd
  FROM params p
  JOIN `ai_usage_analytics.vw_combined_daily_costs` c
    ON c.cost_date BETWEEN p.start_date AND p.end_date
  GROUP BY c.cost_date
)
SELECT
  cost_date,
  total_cost_usd,
  (SELECT daily_budget_usd FROM params) AS budget_reference_usd,
  ROUND((total_cost_usd - (SELECT daily_budget_usd FROM params)) / NULLIF((SELECT daily_budget_usd FROM params), 0) * 100, 2) AS pct_vs_budget
FROM daily_totals
ORDER BY cost_date;
