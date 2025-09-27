-- System Health Monitoring Dashboard for System Administration Panel
-- Provides real-time component health, recovery status, and reliability metrics

CREATE OR REPLACE VIEW `${PROJECT_ID}.${DATASET}.vw_system_health` AS

WITH component_health AS (
  -- Extract component health status from monitoring logs
  SELECT
    TIMESTAMP(JSON_EXTRACT_SCALAR(jsonPayload, '$.timestamp')) AS health_check_time,
    JSON_EXTRACT_SCALAR(jsonPayload, '$.component') AS component_name,
    JSON_EXTRACT_SCALAR(jsonPayload, '$.message') AS health_status,
    CAST(JSON_EXTRACT_SCALAR(jsonPayload, '$.duration_ms') AS FLOAT64) AS response_time_ms,
    JSON_EXTRACT_SCALAR(jsonPayload, '$.request_id') AS request_id
  FROM `${PROJECT_ID}._Default._AllLogs`
  WHERE resource.type = "cloud_function"
  AND JSON_EXTRACT_SCALAR(jsonPayload, '$.logger') = "ai_usage_analytics"
  AND JSON_EXTRACT_SCALAR(jsonPayload, '$.operation') LIKE '%health%'
  AND TIMESTAMP(JSON_EXTRACT_SCALAR(jsonPayload, '$.timestamp')) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
),

circuit_breaker_events AS (
  -- Extract circuit breaker state changes
  SELECT
    TIMESTAMP(JSON_EXTRACT_SCALAR(jsonPayload, '$.timestamp')) AS event_time,
    JSON_EXTRACT_SCALAR(jsonPayload, '$.circuit_name') AS circuit_name,
    JSON_EXTRACT_SCALAR(jsonPayload, '$.message') AS event_description,
    CASE
      WHEN JSON_EXTRACT_SCALAR(jsonPayload, '$.message') LIKE '%opened%' THEN 'open'
      WHEN JSON_EXTRACT_SCALAR(jsonPayload, '$.message') LIKE '%recovered%' THEN 'closed'
      WHEN JSON_EXTRACT_SCALAR(jsonPayload, '$.message') LIKE '%attempting recovery%' THEN 'half_open'
      ELSE 'unknown'
    END AS circuit_state
  FROM `${PROJECT_ID}._Default._AllLogs`
  WHERE resource.type = "cloud_function"
  AND JSON_EXTRACT_SCALAR(jsonPayload, '$.logger') = "ai_usage_analytics"
  AND JSON_EXTRACT_SCALAR(jsonPayload, '$.component') = 'circuit_breaker'
  AND TIMESTAMP(JSON_EXTRACT_SCALAR(jsonPayload, '$.timestamp')) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
),

recovery_operations AS (
  -- Extract recovery operation events
  SELECT
    TIMESTAMP(JSON_EXTRACT_SCALAR(jsonPayload, '$.timestamp')) AS recovery_time,
    JSON_EXTRACT_SCALAR(jsonPayload, '$.operation_id') AS operation_id,
    JSON_EXTRACT_SCALAR(jsonPayload, '$.component') AS component_name,
    JSON_EXTRACT_SCALAR(jsonPayload, '$.scenario') AS failure_scenario,
    CASE
      WHEN JSON_EXTRACT_SCALAR(jsonPayload, '$.message') LIKE '%completed%' THEN 'completed'
      WHEN JSON_EXTRACT_SCALAR(jsonPayload, '$.message') LIKE '%failed%' THEN 'failed'
      ELSE 'in_progress'
    END AS recovery_status,
    CAST(JSON_EXTRACT_SCALAR(jsonPayload, '$.total_duration') AS FLOAT64) AS recovery_duration_seconds
  FROM `${PROJECT_ID}._Default._AllLogs`
  WHERE resource.type = "cloud_function"
  AND JSON_EXTRACT_SCALAR(jsonPayload, '$.logger') = "ai_usage_analytics"
  AND JSON_EXTRACT_SCALAR(jsonPayload, '$.component') = 'recovery_manager'
  AND TIMESTAMP(JSON_EXTRACT_SCALAR(jsonPayload, '$.timestamp')) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
),

pipeline_reliability AS (
  -- Calculate pipeline reliability metrics
  SELECT
    DATE(TIMESTAMP(JSON_EXTRACT_SCALAR(jsonPayload, '$.timestamp'))) AS execution_date,
    COUNT(*) AS total_executions,
    COUNT(CASE WHEN JSON_EXTRACT_SCALAR(jsonPayload, '$.message') LIKE '%completed successfully%' THEN 1 END) AS successful_executions,
    COUNT(CASE WHEN JSON_EXTRACT_SCALAR(jsonPayload, '$.message') LIKE '%failed%' THEN 1 END) AS failed_executions,
    AVG(CAST(JSON_EXTRACT_SCALAR(jsonPayload, '$.processing_time_seconds') AS FLOAT64)) AS avg_processing_time_seconds
  FROM `${PROJECT_ID}._Default._AllLogs`
  WHERE resource.type = "cloud_function"
  AND JSON_EXTRACT_SCALAR(jsonPayload, '$.logger') = "ai_usage_analytics"
  AND JSON_EXTRACT_SCALAR(jsonPayload, '$.operation') = 'run_daily_job'
  AND TIMESTAMP(JSON_EXTRACT_SCALAR(jsonPayload, '$.timestamp')) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  GROUP BY DATE(TIMESTAMP(JSON_EXTRACT_SCALAR(jsonPayload, '$.timestamp')))
)

SELECT
  -- Dashboard metadata
  CURRENT_TIMESTAMP() AS dashboard_generated_at,
  'system_health' AS dashboard_type,

  -- Overall system health status
  CASE
    WHEN (SELECT COUNT(*) FROM circuit_breaker_events WHERE circuit_state = 'open' AND event_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)) > 0 THEN 'unhealthy'
    WHEN (SELECT COUNT(*) FROM circuit_breaker_events WHERE circuit_state = 'half_open' AND event_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)) > 0 THEN 'degraded'
    ELSE 'healthy'
  END AS overall_system_health,

  -- Component health summary
  ARRAY(
    SELECT AS STRUCT
      component_name,
      CASE
        WHEN MAX(health_check_time) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 5 MINUTE) THEN 'healthy'
        WHEN MAX(health_check_time) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 15 MINUTE) THEN 'stale'
        ELSE 'offline'
      END AS health_status,
      MAX(health_check_time) AS last_health_check,
      AVG(response_time_ms) AS avg_response_time_ms,
      COUNT(*) AS health_checks_count
    FROM component_health
    GROUP BY component_name
  ) AS component_health_summary,

  -- Circuit breaker status
  ARRAY(
    SELECT AS STRUCT
      circuit_name,
      circuit_state,
      MAX(event_time) AS last_state_change,
      COUNT(*) AS state_changes_24h
    FROM circuit_breaker_events
    GROUP BY circuit_name, circuit_state
    ORDER BY MAX(event_time) DESC
  ) AS circuit_breaker_status,

  -- Recovery operations summary (last 7 days)
  (SELECT COUNT(*) FROM recovery_operations) AS total_recovery_operations_7d,
  (SELECT COUNT(*) FROM recovery_operations WHERE recovery_status = 'completed') AS successful_recoveries_7d,
  (SELECT COUNT(*) FROM recovery_operations WHERE recovery_status = 'failed') AS failed_recoveries_7d,
  (SELECT SAFE_DIVIDE(COUNT(CASE WHEN recovery_status = 'completed' THEN 1 END), COUNT(*)) * 100 FROM recovery_operations) AS recovery_success_rate,

  -- Pipeline reliability metrics (last 30 days)
  (SELECT SAFE_DIVIDE(SUM(successful_executions), SUM(total_executions)) * 100 FROM pipeline_reliability) AS pipeline_uptime_percentage,
  (SELECT AVG(avg_processing_time_seconds) FROM pipeline_reliability) AS avg_pipeline_duration_seconds,
  (SELECT COUNT(*) FROM pipeline_reliability WHERE DATE(execution_date) = CURRENT_DATE() - 1) AS yesterday_executions,

  -- MTTR (Mean Time To Recovery) calculation
  (
    SELECT AVG(recovery_duration_seconds)
    FROM recovery_operations
    WHERE recovery_status = 'completed'
    AND recovery_duration_seconds IS NOT NULL
  ) AS mean_time_to_recovery_seconds,

  -- System reliability score (0-100)
  LEAST(100,
    COALESCE((SELECT SAFE_DIVIDE(SUM(successful_executions), SUM(total_executions)) * 100 FROM pipeline_reliability), 100) * 0.4 +  -- 40% pipeline success
    COALESCE((SELECT SAFE_DIVIDE(COUNT(CASE WHEN recovery_status = 'completed' THEN 1 END), COUNT(*)) * 100 FROM recovery_operations), 100) * 0.3 +  -- 30% recovery success
    CASE WHEN (SELECT COUNT(*) FROM circuit_breaker_events WHERE circuit_state = 'open' AND event_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)) = 0 THEN 30 ELSE 0 END  -- 30% circuit health
  ) AS system_reliability_score,

  -- Alert summary
  CASE
    WHEN (SELECT COUNT(*) FROM recovery_operations WHERE recovery_status = 'failed' AND recovery_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)) > 0 THEN 'critical'
    WHEN (SELECT COUNT(*) FROM circuit_breaker_events WHERE circuit_state = 'open' AND event_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)) > 0 THEN 'warning'
    ELSE 'normal'
  END AS alert_status,

  -- Recent recovery operations (last 24 hours)
  ARRAY(
    SELECT AS STRUCT
      recovery_time,
      operation_id,
      component_name,
      failure_scenario,
      recovery_status,
      recovery_duration_seconds
    FROM recovery_operations
    WHERE recovery_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
    ORDER BY recovery_time DESC
    LIMIT 20
  ) AS recent_recovery_operations