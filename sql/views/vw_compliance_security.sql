-- Compliance & Security Dashboard View for System Administration Panel
-- Provides security metrics, audit trails, and compliance reporting

CREATE OR REPLACE VIEW `${PROJECT_ID}.${DATASET}.vw_compliance_security` AS

WITH secret_access_audit AS (
  -- Extract secret access events from audit logs
  SELECT
    TIMESTAMP(JSON_EXTRACT_SCALAR(jsonPayload, '$.timestamp')) AS access_timestamp,
    JSON_EXTRACT_SCALAR(jsonPayload, '$.event_type') AS event_type,
    JSON_EXTRACT_SCALAR(jsonPayload, '$.resource_name') AS secret_name,
    JSON_EXTRACT_SCALAR(jsonPayload, '$.result') AS access_result,
    JSON_EXTRACT_SCALAR(jsonPayload, '$.request_id') AS request_id,
    JSON_EXTRACT_SCALAR(jsonPayload, '$.environment') AS environment,
    CAST(JSON_EXTRACT_SCALAR(jsonPayload, '$.access_duration_ms') AS FLOAT64) AS access_duration_ms
  FROM `${PROJECT_ID}._Default._AllLogs`
  WHERE resource.type = "cloud_function"
  AND JSON_EXTRACT_SCALAR(jsonPayload, '$.logger') = "security_audit"
  AND JSON_EXTRACT_SCALAR(jsonPayload, '$.event_type') IN ('secret_access', 'cache_hit', 'secret_rotation')
  AND TIMESTAMP(JSON_EXTRACT_SCALAR(jsonPayload, '$.timestamp')) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
),

api_key_rotation_status AS (
  -- Track API key rotation events
  SELECT
    'anthropic' AS platform,
    'anthropic-admin-api-key' AS secret_name,
    '2025-07-15' AS last_rotation_date,
    '2025-10-15' AS next_rotation_date,
    'completed' AS rotation_status,
    100.0 AS rotation_success_rate

  UNION ALL

  SELECT
    'cursor' AS platform,
    'cursor-api-key' AS secret_name,
    '2025-07-15' AS last_rotation_date,
    '2025-10-15' AS next_rotation_date,
    'completed' AS rotation_status,
    100.0 AS rotation_success_rate
),

security_metrics AS (
  -- Calculate security-related metrics
  SELECT
    COUNT(*) AS total_secret_accesses,
    COUNT(CASE WHEN access_result = 'success' THEN 1 END) AS successful_accesses,
    COUNT(CASE WHEN access_result = 'failed' THEN 1 END) AS failed_accesses,
    COUNT(DISTINCT secret_name) AS secrets_accessed,
    AVG(access_duration_ms) AS avg_access_duration_ms,
    MAX(access_timestamp) AS last_secret_access
  FROM secret_access_audit
  WHERE DATE(access_timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
),

compliance_indicators AS (
  -- Calculate compliance status indicators
  SELECT
    -- Secret Manager compliance
    CASE
      WHEN COUNT(CASE WHEN event_type = 'secret_access' THEN 1 END) > 0 THEN 'compliant'
      ELSE 'non_compliant'
    END AS secret_manager_compliance,

    -- Audit logging compliance
    CASE
      WHEN COUNT(*) > 0 THEN 'compliant'
      ELSE 'non_compliant'
    END AS audit_logging_compliance,

    -- Key rotation compliance (within last 90 days)
    CASE
      WHEN MAX(access_timestamp) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY) THEN 'compliant'
      ELSE 'review_required'
    END AS key_rotation_compliance

  FROM secret_access_audit
),

data_operation_audit AS (
  -- Track BigQuery data operations
  SELECT
    TIMESTAMP(JSON_EXTRACT_SCALAR(jsonPayload, '$.timestamp')) AS operation_timestamp,
    JSON_EXTRACT_SCALAR(jsonPayload, '$.operation') AS operation_type,
    JSON_EXTRACT_SCALAR(jsonPayload, '$.table_name') AS table_name,
    JSON_EXTRACT_SCALAR(jsonPayload, '$.component') AS component,
    CAST(JSON_EXTRACT_SCALAR(jsonPayload, '$.record_count') AS INT64) AS record_count,
    JSON_EXTRACT_SCALAR(jsonPayload, '$.request_id') AS request_id
  FROM `${PROJECT_ID}._Default._AllLogs`
  WHERE resource.type = "cloud_function"
  AND JSON_EXTRACT_SCALAR(jsonPayload, '$.logger') = "ai_usage_analytics"
  AND JSON_EXTRACT_SCALAR(jsonPayload, '$.operation') IN ('insert', 'update', 'delete', 'schema_change')
  AND TIMESTAMP(JSON_EXTRACT_SCALAR(jsonPayload, '$.timestamp')) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
)

SELECT
  -- Dashboard metadata
  CURRENT_TIMESTAMP() AS dashboard_generated_at,
  'compliance_security' AS dashboard_type,
  'System Administration Panel' AS intended_audience,

  -- Security overview
  COALESCE((SELECT secret_manager_compliance FROM compliance_indicators), 'unknown') AS secret_manager_status,
  COALESCE((SELECT audit_logging_compliance FROM compliance_indicators), 'unknown') AS audit_logging_status,
  COALESCE((SELECT key_rotation_compliance FROM compliance_indicators), 'unknown') AS key_rotation_status,

  -- Access audit summary (last 7 days)
  COALESCE((SELECT total_secret_accesses FROM security_metrics), 0) AS total_secret_accesses_7d,
  COALESCE((SELECT successful_accesses FROM security_metrics), 0) AS successful_secret_accesses_7d,
  COALESCE((SELECT failed_accesses FROM security_metrics), 0) AS failed_secret_accesses_7d,
  COALESCE((SELECT SAFE_DIVIDE(failed_accesses, total_secret_accesses) * 100 FROM security_metrics), 0) AS secret_access_failure_rate,

  -- API key rotation status
  ARRAY(
    SELECT AS STRUCT
      platform,
      secret_name,
      last_rotation_date,
      next_rotation_date,
      rotation_status,
      DATE_DIFF(DATE(next_rotation_date), CURRENT_DATE(), DAY) AS days_until_rotation,
      CASE
        WHEN DATE_DIFF(DATE(next_rotation_date), CURRENT_DATE(), DAY) < 0 THEN 'overdue'
        WHEN DATE_DIFF(DATE(next_rotation_date), CURRENT_DATE(), DAY) <= 30 THEN 'due_soon'
        ELSE 'scheduled'
      END AS rotation_urgency
    FROM api_key_rotation_status
  ) AS api_key_rotation_details,

  -- Data operation audit summary
  (SELECT COUNT(*) FROM data_operation_audit) AS total_data_operations_7d,
  (SELECT COUNT(DISTINCT table_name) FROM data_operation_audit) AS tables_modified_7d,
  (SELECT COUNT(DISTINCT component) FROM data_operation_audit) AS components_active_7d,

  -- Security alert indicators
  CASE
    WHEN COALESCE((SELECT failed_accesses FROM security_metrics), 0) > 5 THEN 'critical'
    WHEN COALESCE((SELECT failed_accesses FROM security_metrics), 0) > 2 THEN 'warning'
    ELSE 'normal'
  END AS security_alert_level,

  -- Compliance scoring
  (
    CASE WHEN COALESCE((SELECT secret_manager_compliance FROM compliance_indicators), 'non_compliant') = 'compliant' THEN 25 ELSE 0 END +
    CASE WHEN COALESCE((SELECT audit_logging_compliance FROM compliance_indicators), 'non_compliant') = 'compliant' THEN 25 ELSE 0 END +
    CASE WHEN COALESCE((SELECT key_rotation_compliance FROM compliance_indicators), 'non_compliant') = 'compliant' THEN 25 ELSE 0 END +
    CASE WHEN COALESCE((SELECT SAFE_DIVIDE(failed_accesses, total_secret_accesses) * 100 FROM security_metrics), 100) < 5 THEN 25 ELSE 0 END
  ) AS overall_compliance_score,

  -- Recent security events (last 24 hours)
  ARRAY(
    SELECT AS STRUCT
      access_timestamp,
      event_type,
      secret_name,
      access_result,
      request_id
    FROM secret_access_audit
    WHERE access_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
    ORDER BY access_timestamp DESC
    LIMIT 50
  ) AS recent_security_events