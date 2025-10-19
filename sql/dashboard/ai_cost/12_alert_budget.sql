-- AI Cost Dashboard: Budget Alert Card (users over spend threshold)
WITH params AS (
  SELECT
    COALESCE({{date_range.start}}, DATE '2025-10-01') AS start_date,
    COALESCE({{date_range.end}}, DATE '2025-12-31') AS end_date,
    COALESCE({{user_budget_threshold_usd}}, 500) AS threshold_usd
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
  COUNTIF(total_cost_usd > (SELECT threshold_usd FROM params)) AS users_over_threshold,
  ROUND(MAX(total_cost_usd), 2) AS highest_user_spend_usd
FROM user_totals;
