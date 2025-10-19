-- AI Cost Dashboard: User Distribution Histogram
WITH params AS (
  SELECT
    COALESCE({{date_range.start}}, DATE '2025-10-01') AS start_date,
    COALESCE({{date_range.end}}, DATE '2025-12-31') AS end_date
),
user_totals AS (
  SELECT
    c.user_email,
    SUM(c.amount_usd) AS total_cost_usd
  FROM params p
  JOIN `ai_usage_analytics.vw_combined_daily_costs` c
    ON c.cost_date BETWEEN p.start_date AND p.end_date
  WHERE c.user_email IS NOT NULL
  GROUP BY c.user_email
)
SELECT
  CASE
    WHEN total_cost_usd < 100 THEN '$0-100'
    WHEN total_cost_usd < 300 THEN '$100-300'
    WHEN total_cost_usd < 500 THEN '$300-500'
    WHEN total_cost_usd < 1000 THEN '$500-1000'
    ELSE '$1000+'
  END AS cost_range,
  COUNT(*) AS user_count
FROM user_totals
GROUP BY cost_range
ORDER BY MIN(total_cost_usd);
