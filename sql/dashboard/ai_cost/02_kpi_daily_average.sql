-- AI Cost Dashboard KPI: Daily Average Spend
WITH filtered AS (
  SELECT
    cost_date,
    amount_usd
  FROM `ai_usage_analytics.vw_combined_daily_costs`
  WHERE cost_date >= CAST({{start_date}} AS DATE)
    AND cost_date <= CAST({{end_date}} AS DATE)
),
span AS (
  SELECT
    MIN(cost_date) AS first_date,
    MAX(cost_date) AS last_date,
    DATE_DIFF(MAX(cost_date), MIN(cost_date), DAY) + 1 AS day_count
  FROM filtered
),
totals AS (
  SELECT SUM(amount_usd) AS total_cost
  FROM filtered
)
SELECT
  ROUND(t.total_cost / NULLIF(s.day_count, 0), 2) AS average_daily_cost_usd,
  s.day_count
FROM totals t
CROSS JOIN span s;
