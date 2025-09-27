-- Create all tables script for AI Usage Analytics Dashboard
-- Run this script to create the complete BigQuery schema

-- Set the dataset
-- Note: Replace 'ai_usage' with your actual dataset name if different

-- 1. Raw data tables (partitioned for cost optimization)
\i 01_raw_cursor_usage.sql
\i 02_raw_anthropic_usage.sql
\i 03_raw_anthropic_cost.sql

-- 2. Dimension tables
\i 04_dim_users.sql
\i 05_dim_api_keys.sql

-- 3. Fact tables (normalized metrics)
\i 06_fct_usage_daily.sql
\i 07_fct_cost_daily.sql

-- Create additional indexes and constraints if needed
-- (BigQuery automatically optimizes based on clustering and partitioning)