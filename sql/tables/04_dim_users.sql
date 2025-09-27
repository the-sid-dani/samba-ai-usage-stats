-- User dimension table for cost allocation and analytics

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset}.dim_users` (
  -- Primary key
  user_id STRING NOT NULL,

  -- User details
  email STRING NOT NULL,
  first_name STRING,
  last_name STRING,
  display_name STRING,

  -- Organization details
  department STRING,
  team STRING,
  manager_email STRING,

  -- Status and metadata
  is_active BOOLEAN DEFAULT true,
  created_date DATE,
  updated_date DATE DEFAULT CURRENT_DATE(),

  -- Audit fields
  created_by STRING DEFAULT 'system',
  updated_by STRING DEFAULT 'system',
  updated_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY email, department
OPTIONS (
  description = "User dimension for cost allocation and analytics"
);