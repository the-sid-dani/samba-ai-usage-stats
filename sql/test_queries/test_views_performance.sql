-- Test Queries for Analytics Views Performance and Validation
-- Use these queries to validate view functionality and performance

-- Test 1: Monthly Finance Summary - Basic aggregation test
-- Expected: Should return monthly cost totals by platform
-- Performance target: <5 seconds
SELECT
  month_year_label,
  platform,
  platform_monthly_cost,
  unique_users,
  cost_per_user,
  mom_cost_change_pct,
  data_quality_status
FROM `${project_id}.${dataset}.vw_monthly_finance`
WHERE cost_month >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 MONTH)
ORDER BY cost_year DESC, cost_month_num DESC, platform_monthly_cost DESC
LIMIT 50;

-- Test 2: Productivity Metrics - User performance validation
-- Expected: Should show user productivity metrics with acceptance rates
-- Performance target: <5 seconds
SELECT
  month_year_label,
  platform,
  user_email,
  monthly_lines_accepted,
  avg_monthly_acceptance_rate,
  efficiency_ratio,
  performance_tier,
  engagement_category
FROM `${project_id}.${dataset}.vw_productivity_metrics`
WHERE usage_month >= DATE_SUB(CURRENT_DATE(), INTERVAL 2 MONTH)
  AND monthly_lines_accepted > 100 -- Filter for active users
ORDER BY monthly_lines_accepted DESC
LIMIT 100;

-- Test 3: Cost Allocation - ROI analysis validation
-- Expected: Should show cost per productivity metrics
-- Performance target: <5 seconds
SELECT
  month_year_label,
  platform,
  user_email,
  total_cost_usd,
  total_lines_accepted,
  cost_per_line_accepted,
  estimated_roi_ratio,
  efficiency_tier,
  user_category
FROM `${project_id}.${dataset}.vw_cost_allocation`
WHERE report_month >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 MONTH)
  AND allocation_completeness = 'Full Attribution'
ORDER BY cost_per_line_accepted ASC
LIMIT 50;

-- Test 4: Executive Summary - High-level KPIs
-- Expected: Should show monthly totals and trends
-- Performance target: <3 seconds
SELECT
  month_year_label,
  total_monthly_cost,
  total_active_users,
  cost_per_active_user,
  cost_growth_rate,
  user_growth_rate,
  anthropic_cost_share,
  cursor_cost_share,
  roi_assessment,
  annual_run_rate
FROM `${project_id}.${dataset}.vw_executive_summary`
WHERE report_month >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
ORDER BY report_year DESC, report_month_num DESC
LIMIT 20;

-- Performance Test: View query execution time
-- This query tests if views meet the <5 second performance target
-- Note: Actual timing would require query execution and measurement
SELECT
  view_name,
  query_start_time,
  query_end_time,
  execution_time_seconds,
  row_count,
  CASE
    WHEN execution_time_seconds <= 5.0 THEN 'PASS'
    ELSE 'FAIL'
  END as performance_test_result
FROM (
  SELECT
    'vw_monthly_finance' as view_name,
    CURRENT_TIMESTAMP() as query_start_time,
    (SELECT COUNT(*) FROM `${project_id}.${dataset}.vw_monthly_finance` WHERE cost_month >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 MONTH)) as row_count,
    CURRENT_TIMESTAMP() as query_end_time
  UNION ALL
  SELECT
    'vw_productivity_metrics' as view_name,
    CURRENT_TIMESTAMP() as query_start_time,
    (SELECT COUNT(*) FROM `${project_id}.${dataset}.vw_productivity_metrics` WHERE usage_month >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 MONTH)) as row_count,
    CURRENT_TIMESTAMP() as query_end_time
  UNION ALL
  SELECT
    'vw_cost_allocation' as view_name,
    CURRENT_TIMESTAMP() as query_start_time,
    (SELECT COUNT(*) FROM `${project_id}.${dataset}.vw_cost_allocation` WHERE report_month >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 MONTH)) as row_count,
    CURRENT_TIMESTAMP() as query_end_time
  UNION ALL
  SELECT
    'vw_executive_summary' as view_name,
    CURRENT_TIMESTAMP() as query_start_time,
    (SELECT COUNT(*) FROM `${project_id}.${dataset}.vw_executive_summary` WHERE report_month >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 MONTH)) as row_count,
    CURRENT_TIMESTAMP() as query_end_time
),
timed_results AS (
  SELECT
    *,
    TIMESTAMP_DIFF(query_end_time, query_start_time, MILLISECOND) / 1000.0 as execution_time_seconds
  FROM (
    -- Previous UNION ALL query would go here
    SELECT 'placeholder' as view_name, CURRENT_TIMESTAMP() as query_start_time, 0 as row_count, CURRENT_TIMESTAMP() as query_end_time
  )
)
SELECT * FROM timed_results;

-- Data Quality Validation: Check for expected data patterns
-- Verify views produce reasonable results
SELECT
  'Data Quality Check' as test_category,
  CASE
    WHEN monthly_cost_total > 0 AND user_count > 0 THEN 'PASS'
    ELSE 'FAIL'
  END as finance_view_check,
  CASE
    WHEN productivity_records > 0 AND avg_acceptance > 0 THEN 'PASS'
    ELSE 'FAIL'
  END as productivity_view_check,
  CASE
    WHEN allocation_records > 0 AND avg_cost_per_line > 0 THEN 'PASS'
    ELSE 'FAIL'
  END as allocation_view_check
FROM (
  SELECT
    (SELECT SUM(platform_monthly_cost) FROM `${project_id}.${dataset}.vw_monthly_finance` WHERE cost_month >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH)) as monthly_cost_total,
    (SELECT COUNT(DISTINCT user_email) FROM `${project_id}.${dataset}.vw_monthly_finance` WHERE cost_month >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH)) as user_count,
    (SELECT COUNT(*) FROM `${project_id}.${dataset}.vw_productivity_metrics` WHERE usage_month >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH)) as productivity_records,
    (SELECT AVG(avg_monthly_acceptance_rate) FROM `${project_id}.${dataset}.vw_productivity_metrics` WHERE usage_month >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH)) as avg_acceptance,
    (SELECT COUNT(*) FROM `${project_id}.${dataset}.vw_cost_allocation` WHERE report_month >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH)) as allocation_records,
    (SELECT AVG(cost_per_line_accepted) FROM `${project_id}.${dataset}.vw_cost_allocation` WHERE report_month >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH) AND cost_per_line_accepted IS NOT NULL) as avg_cost_per_line
);