-- Cost Allocation Workbench View
-- Comprehensive cost allocation and ROI analysis for team/project reporting
-- Joins usage and cost data with user attribution for organizational insights

CREATE OR REPLACE VIEW `${project_id}.${dataset}.vw_cost_allocation` AS
WITH user_productivity AS (
  SELECT
    DATE_TRUNC(usage_date, MONTH) as activity_month,
    platform,
    user_email,
    COALESCE(user_id, user_email) as user_identifier,

    -- Productivity metrics
    SUM(lines_of_code_added) as total_lines_added,
    SUM(lines_of_code_accepted) as total_lines_accepted,
    SUM(total_accepts) as total_accepts,
    SUM(sessions) as total_sessions,
    SUM(input_tokens + output_tokens) as total_tokens,

    -- Efficiency calculations
    SAFE_DIVIDE(SUM(lines_of_code_accepted), SUM(lines_of_code_added)) as acceptance_rate,
    SAFE_DIVIDE(SUM(lines_of_code_accepted), SUM(sessions)) as productivity_per_session,

    FROM `${project_id}.${dataset}.fct_usage_daily`
    WHERE usage_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
      AND user_email IS NOT NULL
    GROUP BY 1, 2, 3, 4
),

user_costs AS (
  SELECT
    DATE_TRUNC(cost_date, MONTH) as cost_month,
    platform,
    user_email,
    COALESCE(user_id, user_email) as user_identifier,

    -- Cost aggregations
    SUM(cost_usd) as total_cost_usd,
    COUNT(*) as cost_transactions,
    AVG(cost_usd) as avg_transaction_cost,

    FROM `${project_id}.${dataset}.fct_cost_daily`
    WHERE cost_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
      AND user_email IS NOT NULL
    GROUP BY 1, 2, 3, 4
),

combined_metrics AS (
  SELECT
    COALESCE(up.activity_month, uc.cost_month) as report_month,
    COALESCE(up.platform, uc.platform) as platform,
    COALESCE(up.user_email, uc.user_email) as user_email,
    COALESCE(up.user_identifier, uc.user_identifier) as user_identifier,

    -- Productivity metrics (with nulls for cost-only records)
    COALESCE(up.total_lines_added, 0) as total_lines_added,
    COALESCE(up.total_lines_accepted, 0) as total_lines_accepted,
    COALESCE(up.total_accepts, 0) as total_accepts,
    COALESCE(up.total_sessions, 0) as total_sessions,
    COALESCE(up.total_tokens, 0) as total_tokens,
    up.acceptance_rate,
    up.productivity_per_session,

    -- Cost metrics (with nulls for usage-only records)
    COALESCE(uc.total_cost_usd, 0) as total_cost_usd,
    COALESCE(uc.cost_transactions, 0) as cost_transactions,
    uc.avg_transaction_cost,

    FROM user_productivity up
    FULL OUTER JOIN user_costs uc ON (
      up.activity_month = uc.cost_month
      AND up.platform = uc.platform
      AND up.user_email = uc.user_email
    )
),

roi_calculations AS (
  SELECT
    *,

    -- ROI and efficiency metrics
    SAFE_DIVIDE(total_cost_usd, NULLIF(total_lines_accepted, 0)) as cost_per_line_accepted,
    SAFE_DIVIDE(total_cost_usd, NULLIF(total_sessions, 0)) as cost_per_session,
    SAFE_DIVIDE(total_cost_usd, NULLIF(total_tokens, 0) * 1000) as cost_per_1k_tokens,

    -- Value generation proxy
    CASE
      WHEN total_lines_accepted > 0 THEN
        SAFE_DIVIDE(total_lines_accepted * 50, total_cost_usd) -- Assume $50/hour dev time saved
      ELSE NULL
    END as estimated_roi_ratio,

    -- User activity categorization
    CASE
      WHEN total_sessions >= 50 THEN 'Power User'
      WHEN total_sessions >= 20 THEN 'Regular User'
      WHEN total_sessions >= 5 THEN 'Occasional User'
      WHEN total_sessions > 0 THEN 'Light User'
      ELSE 'Cost Only'
    END as user_category,

    FROM combined_metrics
),

team_aggregations AS (
  SELECT
    report_month,
    platform,

    -- Extract department from email domain (simple heuristic)
    REGEXP_EXTRACT(user_email, r'@(.+)\.') as organization,
    REGEXP_EXTRACT(user_email, r'^([a-zA-Z]+)\.') as department_hint,

    -- Team metrics
    COUNT(DISTINCT user_email) as team_size,
    SUM(total_cost_usd) as team_cost,
    SUM(total_lines_accepted) as team_productivity,
    AVG(acceptance_rate) as team_avg_acceptance_rate,

    -- Team efficiency
    SAFE_DIVIDE(SUM(total_cost_usd), COUNT(DISTINCT user_email)) as cost_per_team_member,
    SAFE_DIVIDE(SUM(total_lines_accepted), COUNT(DISTINCT user_email)) as productivity_per_team_member,

    FROM roi_calculations
    WHERE user_email IS NOT NULL
    GROUP BY 1, 2, 3, 4
)

SELECT
  -- Time dimensions
  r.report_month,
  EXTRACT(YEAR FROM r.report_month) as report_year,
  EXTRACT(MONTH FROM r.report_month) as report_month_num,
  FORMAT_DATE('%Y-%m', r.report_month) as month_year_label,

  -- User and platform dimensions
  r.platform,
  r.user_email,
  r.user_identifier,
  r.user_category,

  -- Core productivity metrics
  r.total_lines_added,
  r.total_lines_accepted,
  r.total_accepts,
  r.total_sessions,
  r.total_tokens,
  r.acceptance_rate,
  r.productivity_per_session,

  -- Cost allocation
  r.total_cost_usd,
  r.cost_transactions,
  r.avg_transaction_cost,

  -- ROI and efficiency analysis
  r.cost_per_line_accepted,
  r.cost_per_session,
  r.cost_per_1k_tokens,
  r.estimated_roi_ratio,

  -- Performance classification
  CASE
    WHEN r.cost_per_line_accepted <= 0.10 THEN 'High Efficiency'
    WHEN r.cost_per_line_accepted <= 0.25 THEN 'Good Efficiency'
    WHEN r.cost_per_line_accepted <= 0.50 THEN 'Average Efficiency'
    ELSE 'Low Efficiency'
  END as efficiency_tier,

  -- Team context
  ta.team_size,
  ta.team_cost,
  ta.team_productivity,
  ta.team_avg_acceptance_rate,
  ta.cost_per_team_member,
  ta.productivity_per_team_member,

  -- User ranking within team
  RANK() OVER (
    PARTITION BY r.report_month, r.platform, ta.organization
    ORDER BY r.total_lines_accepted DESC
  ) as productivity_rank_in_team,

  RANK() OVER (
    PARTITION BY r.report_month, r.platform, ta.organization
    ORDER BY r.cost_per_line_accepted ASC
  ) as efficiency_rank_in_team,

  -- Trend indicators
  LAG(r.total_cost_usd) OVER (
    PARTITION BY r.platform, r.user_email
    ORDER BY EXTRACT(YEAR FROM r.report_month), EXTRACT(MONTH FROM r.report_month)
  ) as prev_month_cost,

  LAG(r.total_lines_accepted) OVER (
    PARTITION BY r.platform, r.user_email
    ORDER BY EXTRACT(YEAR FROM r.report_month), EXTRACT(MONTH FROM r.report_month)
  ) as prev_month_productivity,

  -- Data quality and freshness
  CURRENT_TIMESTAMP() as view_generated_at,

  -- Allocation summary for filtering
  CASE
    WHEN r.total_cost_usd > 0 AND r.total_lines_accepted > 0 THEN 'Full Attribution'
    WHEN r.total_cost_usd > 0 THEN 'Cost Only'
    WHEN r.total_lines_accepted > 0 THEN 'Usage Only'
    ELSE 'No Data'
  END as allocation_completeness

FROM roi_calculations r
LEFT JOIN team_aggregations ta ON (
  r.report_month = ta.report_month
  AND r.platform = ta.platform
  AND REGEXP_EXTRACT(r.user_email, r'@(.+)\.') = ta.organization
)

WHERE r.report_month >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH) -- Last 6 months
  AND (r.total_cost_usd > 0 OR r.total_lines_accepted > 0) -- Has activity

ORDER BY EXTRACT(YEAR FROM r.report_month) DESC, EXTRACT(MONTH FROM r.report_month) DESC, r.total_cost_usd DESC;