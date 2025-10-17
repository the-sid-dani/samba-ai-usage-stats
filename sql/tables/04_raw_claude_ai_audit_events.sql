-- Raw Claude.ai Enterprise audit events table
-- Stores events from claude.ai Enterprise audit logs export
-- Partitioned by event_date for cost optimization

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset}.raw_claude_ai_audit_events` (
  -- Core audit identifiers
  actor_email STRING NOT NULL,
  actor_name STRING,
  event_type STRING NOT NULL,           -- conversation_created, project_created, file_uploaded, message_sent
  event_timestamp TIMESTAMP NOT NULL,
  event_date DATE NOT NULL,             -- Extracted from timestamp for partitioning

  -- Event-specific metadata
  conversation_id STRING,               -- For conversation events
  project_id STRING,                    -- For project events
  file_name STRING,                     -- For file upload events
  file_size INT64,                      -- File size in bytes
  message_count INT64,                  -- Number of messages in conversation

  -- Derived productivity metrics
  estimated_session_minutes INT64,     -- Estimated time spent (derived from event patterns)
  interaction_type STRING,              -- chat, analysis, coding_assistance, document_review

  -- Pipeline metadata
  ingest_date DATE NOT NULL,
  ingest_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  request_id STRING,

  -- Raw audit log data
  raw_response JSON
)
PARTITION BY event_date
CLUSTER BY actor_email, event_type, event_date
OPTIONS (
  description = "Raw claude.ai Enterprise audit events for knowledge worker productivity tracking",
  require_partition_filter = true
);