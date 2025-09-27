-- Monthly Finance Summary View
-- Aggregates costs by platform, user, and month for finance reporting
-- Optimized for Looker Studio dashboard queries

CREATE OR REPLACE VIEW `${project_id}.${dataset}.vw_monthly_finance` AS
WITH monthly_costs AS (
  SELECT
    -- Date dimensions
    DATE_TRUNC(cost_date, MONTH) as cost_month,
    EXTRACT(YEAR FROM cost_date) as cost_year,
    EXTRACT(MONTH FROM cost_date) as cost_month_num,

    -- Platform and user dimensions
    platform,
    user_email,
    COALESCE(user_id, user_email) as user_identifier,
    cost_type,

    -- Cost metrics
    SUM(cost_usd) as total_cost_usd,
    COUNT(*) as total_transactions,
    COUNT(DISTINCT cost_date) as active_days,

    -- Data quality indicators
    MAX(ingest_date) as last_updated,
    COUNT(CASE WHEN user_email IS NOT NULL THEN 1 END) / COUNT(*) as attribution_coverage,

    FROM `${project_id}.${dataset}.fct_cost_daily`
    WHERE cost_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH) -- Last 12 months
    GROUP BY 1, 2, 3, 4, 5, 6, 7
),

platform_totals AS (
  SELECT
    cost_month,
    cost_year,
    cost_month_num,
    platform,

    -- Platform aggregations
    SUM(total_cost_usd) as platform_monthly_cost,
    COUNT(DISTINCT user_identifier) as unique_users,
    AVG(attribution_coverage) as avg_attribution_coverage,

    FROM monthly_costs
    GROUP BY 1, 2, 3, 4
),

user_summaries AS (
  SELECT
    cost_month,
    cost_year,
    cost_month_num,
    user_email,
    user_identifier,

    -- User cost summary across platforms
    SUM(total_cost_usd) as user_monthly_cost,
    COUNT(DISTINCT platform) as platforms_used,
    ARRAY_AGG(DISTINCT platform) as user_platforms,
    MAX(last_updated) as user_last_updated,

    FROM monthly_costs
    WHERE user_email IS NOT NULL
    GROUP BY 1, 2, 3, 4, 5
),

month_over_month AS (
  SELECT
    *,
    LAG(platform_monthly_cost) OVER (
      PARTITION BY platform
      ORDER BY cost_year, cost_month_num
    ) as prev_month_cost,

    -- Calculate month-over-month change
    SAFE_DIVIDE(
      platform_monthly_cost - LAG(platform_monthly_cost) OVER (
        PARTITION BY platform
        ORDER BY cost_year, cost_month_num
      ),
      LAG(platform_monthly_cost) OVER (
        PARTITION BY platform
        ORDER BY cost_year, cost_month_num
      )
    ) as mom_cost_change_pct,

    FROM platform_totals
)

SELECT
  -- Time dimensions
  pt.cost_month,
  pt.cost_year,
  pt.cost_month_num,
  FORMAT_DATE('%Y-%m', pt.cost_month) as month_year_label,

  -- Platform dimensions
  pt.platform,

  -- Cost metrics
  pt.platform_monthly_cost,
  pt.unique_users,
  SAFE_DIVIDE(pt.platform_monthly_cost, pt.unique_users) as cost_per_user,

  -- Growth metrics
  mom.prev_month_cost,
  mom.mom_cost_change_pct,
  CASE
    WHEN mom.mom_cost_change_pct > 0.2 THEN 'High Growth'
    WHEN mom.mom_cost_change_pct > 0.05 THEN 'Moderate Growth'
    WHEN mom.mom_cost_change_pct > -0.05 THEN 'Stable'
    WHEN mom.mom_cost_change_pct > -0.2 THEN 'Moderate Decline'
    ELSE 'Significant Decline'
  END as growth_category,

  -- Data quality metrics
  pt.avg_attribution_coverage,
  CASE
    WHEN pt.avg_attribution_coverage >= 0.95 THEN 'Excellent'
    WHEN pt.avg_attribution_coverage >= 0.85 THEN 'Good'
    WHEN pt.avg_attribution_coverage >= 0.70 THEN 'Acceptable'
    ELSE 'Needs Attention'
  END as data_quality_status,

  -- User activity insights
  ARRAY_AGG(
    STRUCT(
      us.user_email,
      us.user_monthly_cost,
      us.platforms_used,
      us.user_platforms
    ) ORDER BY us.user_monthly_cost DESC LIMIT 10
  ) as top_users_by_cost,

  -- Summary totals for dashboard
  SUM(pt.platform_monthly_cost) OVER (PARTITION BY pt.cost_month) as total_monthly_cost,

  -- Data freshness
  CURRENT_TIMESTAMP() as view_generated_at,
  DATE_DIFF(CURRENT_DATE(), MAX(DATE(fcd.ingest_date)), DAY) as days_since_last_data_refresh

FROM platform_totals pt
LEFT JOIN month_over_month mom ON (
  pt.cost_month = mom.cost_month
  AND pt.platform = mom.platform
)
LEFT JOIN user_summaries us ON (
  pt.cost_month = us.cost_month
  AND pt.platform IN UNNEST(us.user_platforms)
)
LEFT JOIN `${project_id}.${dataset}.fct_cost_daily` fcd ON (
  pt.platform = fcd.platform
  AND pt.cost_month = DATE_TRUNC(fcd.cost_date, MONTH)
)

GROUP BY
  pt.cost_month, pt.cost_year, pt.cost_month_num, pt.platform,
  pt.platform_monthly_cost, pt.unique_users, pt.avg_attribution_coverage,
  mom.prev_month_cost, mom.mom_cost_change_pct

ORDER BY pt.cost_year DESC, pt.cost_month_num DESC, pt.platform_monthly_cost DESC;