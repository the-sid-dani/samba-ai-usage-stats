-- AI Cost Dashboard: Team Attribution Table
WITH user_costs AS (
  SELECT
    user_email,
    SUM(amount_usd) AS total_cost_usd
  FROM `ai_usage_analytics.vw_combined_daily_costs`
  WHERE cost_date >= CAST({{start_date}} AS DATE)
    AND cost_date <= CAST({{end_date}} AS DATE)
    AND user_email IS NOT NULL
  GROUP BY user_email
),
team_mapping AS (
  SELECT
    LOWER(mapped_user_email) AS mapped_user_email,
    COALESCE(mapped_team_name, 'Unmapped') AS team
  FROM `ai_usage_analytics.dim_api_keys`
  WHERE mapped_user_email IS NOT NULL
),
joined AS (
  SELECT
    COALESCE(m.team, 'Unmapped') AS team,
    uc.user_email,
    uc.total_cost_usd
  FROM user_costs uc
  LEFT JOIN team_mapping m
    ON LOWER(uc.user_email) = m.mapped_user_email
)
SELECT
  team,
  COUNT(DISTINCT user_email) AS user_count,
  ROUND(SUM(total_cost_usd), 2) AS team_cost_usd,
  ROUND(SUM(total_cost_usd) / NULLIF(COUNT(DISTINCT user_email), 0), 2) AS cost_per_user_usd,
  ARRAY_AGG(STRUCT(user_email, total_cost_usd) ORDER BY total_cost_usd DESC LIMIT 1)[OFFSET(0)].user_email AS top_user,
  ARRAY_AGG(STRUCT(user_email, total_cost_usd) ORDER BY total_cost_usd DESC LIMIT 1)[OFFSET(0)].total_cost_usd AS top_user_cost_usd
FROM joined
GROUP BY team
ORDER BY team_cost_usd DESC;
