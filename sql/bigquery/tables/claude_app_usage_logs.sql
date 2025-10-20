-- Claude App Usage Logs Table
-- Tracks user interactions with Claude.ai for productivity metrics
--
-- Source: Claude.ai admin activity export
-- Update Frequency: Manual/batch load
-- Primary Use: Productivity metrics, user engagement analysis

CREATE TABLE IF NOT EXISTS `ai-workflows-459123.ai_usage_analytics.claude_app_usage_logs` (
  -- Timestamp
  activity_timestamp TIMESTAMP NOT NULL,
  activity_date DATE NOT NULL,

  -- User Information
  user_email STRING NOT NULL,
  user_name STRING,
  user_uuid STRING NOT NULL,

  -- Event Information
  event_type STRING NOT NULL,  -- conversation_created, file_uploaded, project_created, etc.
  event_info JSON,  -- Additional event-specific data

  -- Entity Information
  entity_type STRING,  -- chat_conversation, file, chat_project, etc.
  entity_uuid STRING,
  conversation_uuid STRING,  -- NULL for non-conversation events
  project_uuid STRING,  -- NULL for non-project events

  -- Context Information
  client_platform STRING,  -- desktop_app, web_claude_ai, ios, android
  device_id STRING,
  user_agent STRING,
  ip_address STRING,

  -- Metadata
  ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  data_source STRING DEFAULT 'claude_activity_export'
)
PARTITION BY activity_date
CLUSTER BY user_email, event_type, client_platform
OPTIONS(
  description='Claude app usage logs for productivity metrics and user engagement analysis',
  labels=[("source", "claude_admin_export"), ("category", "productivity")]
);

-- Create indexes for common queries
-- BigQuery doesn't use explicit indexes but clustering helps with:
-- 1. User-specific queries (user_email)
-- 2. Event type analysis (event_type)
-- 3. Platform usage (client_platform)
