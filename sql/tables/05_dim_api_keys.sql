-- API key mapping dimension table for user attribution

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset}.dim_api_keys` (
  -- Primary identifiers
  api_key_id STRING NOT NULL,
  api_key_name STRING,

  -- User attribution
  user_email STRING NOT NULL,
  user_id STRING,

  -- API key details
  platform STRING NOT NULL, -- 'anthropic', 'cursor', etc.
  workspace_id STRING,
  purpose STRING, -- e.g., 'development', 'production', 'testing'

  -- Status and validity
  is_active BOOLEAN DEFAULT true,
  created_date DATE,
  expires_date DATE,

  -- Metadata
  notes STRING,
  updated_date DATE DEFAULT CURRENT_DATE(),
  updated_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),

  -- Audit fields
  created_by STRING DEFAULT 'google_sheets_import',
  updated_by STRING DEFAULT 'google_sheets_import'
)
CLUSTER BY platform, user_email, api_key_id
OPTIONS (
  description = "API key mappings for user attribution from Google Sheets"
);