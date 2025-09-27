-- Data Quality Dashboard View for System Administration Panel
-- Provides comprehensive data quality metrics for monitoring and alerting

CREATE OR REPLACE VIEW `${PROJECT_ID}.${DATASET}.vw_data_quality_dashboard` AS

WITH quality_metrics AS (
  SELECT
    measurement_date,
    platform,
    overall_score,
    completeness_score,
    accuracy_score,
    freshness_score,
    consistency_score,
    validity_score,
    created_at,

    -- Quality status indicators
    CASE
      WHEN overall_score >= 90 THEN 'excellent'
      WHEN overall_score >= 75 THEN 'good'
      WHEN overall_score >= 60 THEN 'fair'
      ELSE 'poor'
    END AS quality_status,

    -- Alert indicators
    CASE
      WHEN overall_score < 60 THEN 'critical'
      WHEN overall_score < 75 THEN 'warning'
      ELSE 'normal'
    END AS alert_level

  FROM `${PROJECT_ID}.${DATASET}.data_quality_metrics`
  WHERE measurement_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
),

data_freshness AS (
  SELECT
    'usage_data' AS data_type,
    'fct_usage_daily' AS table_name,
    MAX(DATE(usage_date)) AS latest_data_date,
    DATE_DIFF(CURRENT_DATE(), MAX(DATE(usage_date)), DAY) AS days_behind,
    DATETIME_DIFF(CURRENT_DATETIME(), MAX(DATETIME(ingest_date)), HOUR) AS hours_behind
  FROM `${PROJECT_ID}.${DATASET}.fct_usage_daily`
  WHERE DATE(usage_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)

  UNION ALL

  SELECT
    'cost_data' AS data_type,
    'fct_cost_daily' AS table_name,
    MAX(DATE(cost_date)) AS latest_data_date,
    DATE_DIFF(CURRENT_DATE(), MAX(DATE(cost_date)), DAY) AS days_behind,
    DATETIME_DIFF(CURRENT_DATETIME(), MAX(DATETIME(ingest_date)), HOUR) AS hours_behind
  FROM `${PROJECT_ID}.${DATASET}.fct_cost_daily`
  WHERE DATE(cost_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
),

validation_errors AS (
  SELECT
    DATE(usage_date) AS error_date,
    platform,
    COUNT(*) AS total_records,
    -- Placeholder validation error counts (would be from actual validation results)
    0 AS validation_errors,
    0 AS schema_errors,
    0 AS business_rule_errors
  FROM `${PROJECT_ID}.${DATASET}.fct_usage_daily`
  WHERE DATE(usage_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  GROUP BY DATE(usage_date), platform
),

attribution_completeness AS (
  SELECT
    DATE(usage_date) AS metric_date,
    platform,
    COUNT(*) AS total_records,
    COUNT(user_email) AS attributed_records,
    SAFE_DIVIDE(COUNT(user_email), COUNT(*)) * 100 AS attribution_rate
  FROM `${PROJECT_ID}.${DATASET}.fct_usage_daily`
  WHERE DATE(usage_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  GROUP BY DATE(usage_date), platform
)

SELECT
  -- Time dimensions
  CURRENT_DATETIME() AS dashboard_generated_at,
  DATE(CURRENT_DATETIME()) AS report_date,

  -- Overall quality metrics (latest day)
  (SELECT AVG(overall_score) FROM quality_metrics WHERE measurement_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)) AS overall_quality_score,
  (SELECT AVG(completeness_score) FROM quality_metrics WHERE measurement_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)) AS avg_completeness_score,
  (SELECT AVG(accuracy_score) FROM quality_metrics WHERE measurement_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)) AS avg_accuracy_score,
  (SELECT AVG(freshness_score) FROM quality_metrics WHERE measurement_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)) AS avg_freshness_score,

  -- Data freshness indicators
  (SELECT MAX(hours_behind) FROM data_freshness) AS max_hours_behind,
  (SELECT COUNT(*) FROM data_freshness WHERE hours_behind > 25) AS stale_tables_count,

  -- Error rate indicators
  (SELECT AVG(validation_errors) FROM validation_errors WHERE error_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)) AS avg_validation_errors,
  (SELECT SUM(validation_errors) FROM validation_errors WHERE error_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)) AS total_weekly_errors,

  -- Attribution completeness
  (SELECT AVG(attribution_rate) FROM attribution_completeness WHERE metric_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)) AS avg_attribution_rate,
  (SELECT COUNT(*) FROM attribution_completeness WHERE metric_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY) AND attribution_rate < 95) AS platforms_below_attribution_target,

  -- Quality trends (7-day)
  (
    SELECT AVG(overall_score)
    FROM quality_metrics
    WHERE measurement_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  ) AS weekly_avg_quality_score,

  -- Alert indicators
  CASE
    WHEN (SELECT AVG(overall_score) FROM quality_metrics WHERE measurement_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)) < 60 THEN 'critical'
    WHEN (SELECT AVG(overall_score) FROM quality_metrics WHERE measurement_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)) < 75 THEN 'warning'
    WHEN (SELECT MAX(hours_behind) FROM data_freshness) > 25 THEN 'warning'
    ELSE 'normal'
  END AS overall_alert_status,

  -- Quality improvement recommendations
  ARRAY(
    SELECT AS STRUCT
      platform,
      overall_score,
      CASE
        WHEN completeness_score < 90 THEN 'Improve user attribution mapping'
        WHEN accuracy_score < 90 THEN 'Review data validation rules'
        WHEN freshness_score < 90 THEN 'Optimize data pipeline timing'
        ELSE 'No immediate action required'
      END AS recommendation
    FROM quality_metrics
    WHERE measurement_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
    AND overall_score < 85
  ) AS improvement_recommendations