-- Executive Summary View
-- High-level KPIs and summary metrics for executive dashboard
-- Combines cost, usage, and productivity data into executive-ready insights

CREATE OR REPLACE VIEW `${project_id}.${dataset}.vw_executive_summary` AS
WITH monthly_summary AS (
  SELECT
    DATE_TRUNC(cost_date, MONTH) as report_month,
    EXTRACT(YEAR FROM cost_date) as report_year,
    EXTRACT(MONTH FROM cost_date) as report_month_num,

    -- Overall cost metrics
    SUM(cost_usd) as total_monthly_cost,
    COUNT(DISTINCT user_email) as active_cost_users,
    COUNT(DISTINCT platform) as platforms_used,

    -- Platform breakdown
    SUM(CASE WHEN platform = 'anthropic' THEN cost_usd ELSE 0 END) as anthropic_cost,
    SUM(CASE WHEN platform = 'cursor' THEN cost_usd ELSE 0 END) as cursor_cost,

    FROM `${project_id}.${dataset}.fct_cost_daily`
    WHERE cost_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
      AND user_email IS NOT NULL
    GROUP BY 1, 2, 3
),

usage_summary AS (
  SELECT
    DATE_TRUNC(usage_date, MONTH) as report_month,

    -- Usage metrics
    COUNT(DISTINCT user_email) as active_usage_users,
    SUM(sessions) as total_sessions,
    SUM(lines_of_code_accepted) as total_lines_accepted,
    SUM(input_tokens + output_tokens) as total_tokens,

    -- Platform-specific usage
    SUM(CASE WHEN platform = 'anthropic' THEN input_tokens + output_tokens ELSE 0 END) as anthropic_tokens,
    SUM(CASE WHEN platform = 'cursor' THEN lines_of_code_accepted ELSE 0 END) as cursor_lines_accepted,

    -- Productivity indicators
    AVG(acceptance_rate) as avg_acceptance_rate,
    SAFE_DIVIDE(SUM(lines_of_code_accepted), SUM(sessions)) as avg_productivity_per_session,

    FROM `${project_id}.${dataset}.fct_usage_daily`
    WHERE usage_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
      AND user_email IS NOT NULL
    GROUP BY 1
),

growth_trends AS (
  SELECT
    *,
    LAG(total_monthly_cost) OVER (ORDER BY report_year, report_month_num) as prev_month_cost,
    LAG(active_cost_users) OVER (ORDER BY report_year, report_month_num) as prev_month_users,

    FROM monthly_summary
),

roi_metrics AS (
  SELECT
    ms.report_month,
    ms.report_year,
    ms.report_month_num,

    -- Join cost and usage data
    ms.total_monthly_cost,
    ms.active_cost_users,
    us.active_usage_users,
    GREATEST(ms.active_cost_users, us.active_usage_users) as total_active_users,

    -- Usage metrics
    us.total_sessions,
    us.total_lines_accepted,
    us.total_tokens,
    us.avg_acceptance_rate,
    us.avg_productivity_per_session,

    -- Platform breakdown
    ms.anthropic_cost,
    ms.cursor_cost,
    us.anthropic_tokens,
    us.cursor_lines_accepted,

    -- ROI calculations
    SAFE_DIVIDE(ms.total_monthly_cost, us.total_lines_accepted) as cost_per_line_accepted,
    SAFE_DIVIDE(ms.total_monthly_cost, us.total_sessions) as cost_per_session,
    SAFE_DIVIDE(ms.total_monthly_cost, GREATEST(ms.active_cost_users, us.active_usage_users)) as cost_per_active_user,

    -- Efficiency ratios
    SAFE_DIVIDE(us.total_lines_accepted * 50, ms.total_monthly_cost) as estimated_time_savings_ratio, -- $50/hour assumption

    FROM monthly_summary ms
    LEFT JOIN usage_summary us ON ms.report_month = us.report_month
)

SELECT
  -- Time dimensions
  rm.report_month,
  rm.report_year,
  rm.report_month_num,
  FORMAT_DATE('%Y-%m', rm.report_month) as month_year_label,
  FORMAT_DATE('%B %Y', rm.report_month) as month_name_year,

  -- Executive KPIs
  rm.total_monthly_cost,
  rm.total_active_users,
  rm.cost_per_active_user,

  -- Growth indicators
  gt.prev_month_cost,
  gt.prev_month_users,
  SAFE_DIVIDE(rm.total_monthly_cost - gt.prev_month_cost, NULLIF(gt.prev_month_cost, 0)) as cost_growth_rate,
  SAFE_DIVIDE(rm.total_active_users - gt.prev_month_users, NULLIF(gt.prev_month_users, 0)) as user_growth_rate,

  -- Platform insights
  rm.anthropic_cost,
  rm.cursor_cost,
  SAFE_DIVIDE(rm.anthropic_cost, rm.total_monthly_cost) as anthropic_cost_share,
  SAFE_DIVIDE(rm.cursor_cost, rm.total_monthly_cost) as cursor_cost_share,

  -- Productivity metrics
  rm.total_sessions,
  rm.total_lines_accepted,
  rm.total_tokens,
  rm.avg_acceptance_rate,
  rm.avg_productivity_per_session,

  -- ROI and efficiency
  rm.cost_per_line_accepted,
  rm.cost_per_session,
  rm.estimated_time_savings_ratio,

  -- Business insights
  CASE
    WHEN rm.cost_per_line_accepted <= 0.15 THEN 'Excellent ROI'
    WHEN rm.cost_per_line_accepted <= 0.30 THEN 'Good ROI'
    WHEN rm.cost_per_line_accepted <= 0.50 THEN 'Acceptable ROI'
    ELSE 'Poor ROI'
  END as roi_assessment,

  CASE
    WHEN rm.total_active_users >= gt.prev_month_users * 1.1 THEN 'Growing Team'
    WHEN rm.total_active_users >= gt.prev_month_users * 0.9 THEN 'Stable Team'
    ELSE 'Shrinking Team'
  END as team_trend,

  -- Platform utilization insights
  CASE
    WHEN SAFE_DIVIDE(rm.anthropic_cost, rm.total_monthly_cost) > 0.7 THEN 'Anthropic Heavy'
    WHEN SAFE_DIVIDE(rm.cursor_cost, rm.total_monthly_cost) > 0.7 THEN 'Cursor Heavy'
    ELSE 'Balanced Usage'
  END as platform_preference,

  -- Budget and forecasting helpers
  rm.total_monthly_cost * 12 as annual_run_rate,
  rm.cost_per_active_user * rm.total_active_users * 12 as annual_cost_forecast,

  -- Quarter-to-date and year-to-date calculations
  SUM(rm.total_monthly_cost) OVER (
    PARTITION BY EXTRACT(YEAR FROM rm.report_month), CAST(CEILING(EXTRACT(MONTH FROM rm.report_month) / 3.0) AS INT64)
    ORDER BY EXTRACT(MONTH FROM rm.report_month)
    ROWS UNBOUNDED PRECEDING
  ) as qtd_cost,

  SUM(rm.total_monthly_cost) OVER (
    PARTITION BY EXTRACT(YEAR FROM rm.report_month)
    ORDER BY EXTRACT(MONTH FROM rm.report_month)
    ROWS UNBOUNDED PRECEDING
  ) as ytd_cost,

  -- Data quality indicators
  CURRENT_TIMESTAMP() as view_generated_at,
  DATE_DIFF(CURRENT_DATE(), MAX(DATE(fcd.ingest_date)), DAY) as days_since_last_refresh,

  -- Summary flags for dashboard filtering
  CASE
    WHEN rm.total_monthly_cost > 0 AND rm.total_lines_accepted > 0 THEN 'Complete Data'
    WHEN rm.total_monthly_cost > 0 THEN 'Cost Data Only'
    WHEN rm.total_lines_accepted > 0 THEN 'Usage Data Only'
    ELSE 'No Data'
  END as data_completeness

FROM roi_metrics rm
LEFT JOIN growth_trends gt ON (
  rm.report_month = gt.report_month
  AND rm.report_year = gt.report_year
  AND rm.report_month_num = gt.report_month_num
)
LEFT JOIN `${project_id}.${dataset}.fct_cost_daily` fcd ON (
  DATE_TRUNC(fcd.cost_date, MONTH) = rm.report_month
)

WHERE rm.report_month >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH) -- Last 12 months

GROUP BY
  rm.report_month, rm.report_year, rm.report_month_num,
  rm.total_monthly_cost, rm.total_active_users, rm.cost_per_active_user,
  gt.prev_month_cost, gt.prev_month_users,
  rm.anthropic_cost, rm.cursor_cost,
  rm.total_sessions, rm.total_lines_accepted, rm.total_tokens,
  rm.avg_acceptance_rate, rm.avg_productivity_per_session,
  rm.cost_per_line_accepted, rm.cost_per_session, rm.estimated_time_savings_ratio

ORDER BY rm.report_year DESC, rm.report_month_num DESC;