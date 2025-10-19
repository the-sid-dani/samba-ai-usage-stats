-- AI Cost Dashboard: Top 15 Users by Spend
WITH params AS (
  SELECT
    COALESCE({{date_range.start}}, DATE '2025-10-01') AS start_date,
    COALESCE({{date_range.end}}, DATE '2025-12-31') AS end_date,
    COALESCE({{alert_threshold_usd}}, 500) AS alert_threshold_usd
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
  user_email,
  ROUND(total_cost_usd, 2) AS total_cost_usd,
  (SELECT alert_threshold_usd FROM params) AS alert_threshold_usd
FROM user_totals
ORDER BY total_cost_usd DESC
LIMIT 15;
