-- Productivity Metrics View
-- Engineering productivity analytics for development team insights
-- Optimized for engineering dashboard queries with acceptance rates and trends

CREATE OR REPLACE VIEW `${project_id}.${dataset}.vw_productivity_metrics` AS
WITH daily_user_metrics AS (
  SELECT
    -- Time dimensions
    usage_date,
    DATE_TRUNC(usage_date, WEEK(MONDAY)) as usage_week,
    DATE_TRUNC(usage_date, MONTH) as usage_month,
    EXTRACT(YEAR FROM usage_date) as usage_year,
    EXTRACT(MONTH FROM usage_date) as usage_month_num,

    -- User and platform dimensions
    platform,
    user_email,
    COALESCE(user_id, user_email) as user_identifier,
    model,

    -- Productivity metrics
    SUM(sessions) as daily_sessions,
    SUM(input_tokens + output_tokens) as total_tokens,
    SUM(lines_of_code_added) as daily_lines_added,
    SUM(lines_of_code_accepted) as daily_lines_accepted,
    SUM(total_accepts) as daily_accepts,

    -- Calculate daily acceptance rate
    SAFE_DIVIDE(
      SUM(lines_of_code_accepted),
      NULLIF(SUM(lines_of_code_added), 0)
    ) as daily_acceptance_rate,

    -- Usage intensity metrics
    SUM(subscription_requests + usage_based_requests) as total_requests,
    AVG(acceptance_rate) as avg_session_acceptance_rate,

    -- Data quality
    MAX(ingest_date) as last_updated,

    FROM `${project_id}.${dataset}.fct_usage_daily`
    WHERE usage_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH) -- Last 6 months
      AND user_email IS NOT NULL -- Only attributed data
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9
),

weekly_trends AS (
  SELECT
    usage_week,
    platform,
    user_email,

    -- Weekly aggregations
    SUM(daily_sessions) as weekly_sessions,
    SUM(total_tokens) as weekly_tokens,
    SUM(daily_lines_added) as weekly_lines_added,
    SUM(daily_lines_accepted) as weekly_lines_accepted,
    AVG(daily_acceptance_rate) as avg_weekly_acceptance_rate,

    -- Activity consistency
    COUNT(DISTINCT usage_date) as active_days_in_week,
    COUNT(DISTINCT usage_date) / 7.0 as weekly_consistency_rate,

    FROM daily_user_metrics
    GROUP BY 1, 2, 3
),

monthly_productivity AS (
  SELECT
    usage_month,
    usage_year,
    usage_month_num,
    platform,
    user_email,

    -- Monthly productivity metrics
    SUM(daily_sessions) as monthly_sessions,
    SUM(total_tokens) as monthly_tokens,
    SUM(daily_lines_added) as monthly_lines_added,
    SUM(daily_lines_accepted) as monthly_lines_accepted,
    AVG(daily_acceptance_rate) as avg_monthly_acceptance_rate,

    -- Productivity trends
    LAG(SUM(daily_lines_accepted)) OVER (
      PARTITION BY platform, user_email
      ORDER BY usage_year, usage_month_num
    ) as prev_month_lines_accepted,

    -- User engagement
    COUNT(DISTINCT usage_date) as active_days_in_month,
    COUNT(DISTINCT usage_date) / DATE_DIFF(
      LAST_DAY(usage_month),
      DATE_TRUNC(usage_month, MONTH),
      DAY
    ) as monthly_engagement_rate,

    FROM daily_user_metrics
    GROUP BY 1, 2, 3, 4, 5
),

platform_benchmarks AS (
  SELECT
    usage_month,
    platform,

    -- Platform benchmarks
    AVG(avg_monthly_acceptance_rate) as platform_avg_acceptance_rate,
    STDDEV(avg_monthly_acceptance_rate) as platform_acceptance_std,
    APPROX_QUANTILES(avg_monthly_acceptance_rate, 4)[OFFSET(2)] as platform_median_acceptance,
    APPROX_QUANTILES(avg_monthly_acceptance_rate, 4)[OFFSET(1)] as platform_p25_acceptance,
    APPROX_QUANTILES(avg_monthly_acceptance_rate, 4)[OFFSET(3)] as platform_p75_acceptance,

    FROM monthly_productivity
    WHERE avg_monthly_acceptance_rate IS NOT NULL
    GROUP BY 1, 2
)

SELECT
  -- Time dimensions
  mp.usage_month,
  mp.usage_year,
  mp.usage_month_num,
  FORMAT_DATE('%Y-%m', mp.usage_month) as month_year_label,

  -- Platform and user dimensions
  mp.platform,
  mp.user_email,

  -- Core productivity metrics
  mp.monthly_sessions,
  mp.monthly_tokens,
  mp.monthly_lines_added,
  mp.monthly_lines_accepted,
  mp.avg_monthly_acceptance_rate,

  -- Productivity efficiency
  SAFE_DIVIDE(mp.monthly_lines_accepted, mp.monthly_sessions) as lines_per_session,
  SAFE_DIVIDE(mp.monthly_tokens, mp.monthly_sessions) as tokens_per_session,
  SAFE_DIVIDE(mp.monthly_lines_accepted, mp.monthly_tokens) as efficiency_ratio,

  -- Growth trends
  mp.prev_month_lines_accepted,
  SAFE_DIVIDE(
    mp.monthly_lines_accepted - mp.prev_month_lines_accepted,
    NULLIF(mp.prev_month_lines_accepted, 0)
  ) as mom_productivity_change_pct,

  -- Engagement metrics
  mp.active_days_in_month,
  mp.monthly_engagement_rate,
  CASE
    WHEN mp.monthly_engagement_rate >= 0.8 THEN 'Highly Active'
    WHEN mp.monthly_engagement_rate >= 0.5 THEN 'Moderately Active'
    WHEN mp.monthly_engagement_rate >= 0.2 THEN 'Occasional'
    ELSE 'Low Activity'
  END as engagement_category,

  -- Performance benchmarking
  pb.platform_avg_acceptance_rate,
  pb.platform_median_acceptance,
  CASE
    WHEN mp.avg_monthly_acceptance_rate >= pb.platform_p75_acceptance THEN 'Top Performer'
    WHEN mp.avg_monthly_acceptance_rate >= pb.platform_median_acceptance THEN 'Above Average'
    WHEN mp.avg_monthly_acceptance_rate >= pb.platform_p25_acceptance THEN 'Below Average'
    ELSE 'Needs Support'
  END as performance_tier,

  -- Weekly trend analysis
  wt.avg_weekly_acceptance_rate,
  wt.weekly_consistency_rate,

  -- Data freshness indicators
  CURRENT_TIMESTAMP() as view_generated_at,
  DATE_DIFF(CURRENT_DATE(), CURRENT_DATE(), DAY) as days_since_last_refresh

FROM monthly_productivity mp
LEFT JOIN platform_benchmarks pb ON (
  mp.usage_month = pb.usage_month
  AND mp.platform = pb.platform
)
LEFT JOIN (
  SELECT
    DATE_TRUNC(usage_week, MONTH) as month_ref,
    platform,
    user_email,
    AVG(avg_weekly_acceptance_rate) as avg_weekly_acceptance_rate,
    AVG(weekly_consistency_rate) as weekly_consistency_rate
  FROM weekly_trends
  WHERE usage_week >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
  GROUP BY 1, 2, 3
) wt ON (
  mp.usage_month = wt.month_ref
  AND mp.platform = wt.platform
  AND mp.user_email = wt.user_email
)

WHERE mp.usage_month >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH) -- Last 6 months for dashboard
  AND mp.monthly_lines_added > 0 -- Filter out inactive periods

ORDER BY mp.usage_year DESC, mp.usage_month_num DESC, mp.monthly_lines_accepted DESC;