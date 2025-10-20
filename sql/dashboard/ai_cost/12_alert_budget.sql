-- AI Cost Dashboard: Budget Alert Card (users over spend threshold)
WITH user_totals AS (
  SELECT
    user_email,
    SUM(amount_usd) AS total_cost_usd
  FROM `ai_usage_analytics.vw_combined_daily_costs`
  WHERE cost_date >= CAST({{start_date}} AS DATE)
    AND cost_date <= CAST({{end_date}} AS DATE)
    AND user_email IS NOT NULL
  GROUP BY user_email
)
SELECT
  COUNTIF(total_cost_usd > {{user_budget_threshold_usd}}) AS users_over_threshold,
  ROUND(MAX(total_cost_usd), 2) AS highest_user_spend_usd
FROM user_totals;
