-- AI Cost Dashboard KPI: Daily Average Spend
WITH params AS (
  SELECT
    COALESCE({{date_range.start}}, DATE '2025-10-01') AS start_date,
    COALESCE({{date_range.end}}, DATE '2025-12-31') AS end_date
),
span AS (
  SELECT start_date, end_date, DATE_DIFF(end_date, start_date) + 1 AS day_count
  FROM params
),
totals AS (
  SELECT SUM(amount_usd) AS total_cost
  FROM params p
  JOIN `ai_usage_analytics.vw_combined_daily_costs` c
    ON c.cost_date BETWEEN p.start_date AND p.end_date
)
SELECT
  ROUND(t.total_cost / NULLIF(s.day_count, 0), 2) AS average_daily_cost_usd,
  s.day_count
FROM totals t
JOIN span s ON 1=1;
