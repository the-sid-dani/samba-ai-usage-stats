-- Enhanced User Dimension Table
-- Comprehensive user data with organizational hierarchy for advanced analytics
-- Optimized for Metabase drill-down capabilities

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset}.dim_users_enhanced` (
  -- Primary identifiers
  user_sk INT64 NOT NULL,                  -- surrogate key
  user_email STRING NOT NULL,              -- primary identifier
  first_name STRING,
  last_name STRING,
  full_name STRING,                        -- computed: first + last
  display_name STRING,                     -- for UI display

  -- Organizational hierarchy (Metabase drill-down)
  department STRING,                       -- Engineering, Product, Marketing
  sub_department STRING,                   -- Backend, Frontend, Data, QA
  team STRING,                             -- specific team assignment
  job_level STRING,                        -- Junior, Mid, Senior, Staff, Principal
  manager_email STRING,                    -- for hierarchy analysis
  director_email STRING,                   -- department head

  -- AI usage context
  ai_user_type STRING,                     -- engineering, knowledge_worker, hybrid
  primary_ai_tools ARRAY<STRING>,          -- [cursor, claude_code, claude_api]
  ai_budget_monthly_usd FLOAT64,           -- allocated AI budget

  -- Status and lifecycle
  is_active BOOLEAN DEFAULT true,
  start_date DATE,
  end_date DATE,

  -- Metadata
  created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY department, team, user_email
OPTIONS (
  description = "Enhanced user dimension with organizational hierarchy"
);