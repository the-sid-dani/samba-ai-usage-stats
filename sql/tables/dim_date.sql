-- Date Dimension Table
-- Time dimension optimized for Metabase filtering and fiscal reporting
-- Pre-populated with calendar data for efficient dashboard queries

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset}.dim_date` (
  -- Primary identifiers
  date_sk INT64 NOT NULL,                  -- YYYYMMDD format (20250927)
  calendar_date DATE NOT NULL,             -- actual date (2025-09-27)

  -- Calendar hierarchy
  year_num INT64,                          -- 2025
  quarter_num INT64,                       -- 1, 2, 3, 4
  month_num INT64,                         -- 1-12
  month_name STRING,                       -- January, February
  week_num INT64,                          -- 1-53
  day_of_week INT64,                       -- 1-7 (Monday=1)
  day_name STRING,                         -- Monday, Tuesday

  -- Business context
  is_weekend BOOLEAN,
  is_business_day BOOLEAN,
  is_holiday BOOLEAN,
  fiscal_year INT64,                       -- fiscal year
  fiscal_quarter INT64,                    -- fiscal quarter

  -- Metabase-friendly labels
  year_month_label STRING,                 -- "2025-09"
  quarter_label STRING,                    -- "Q3 2025"
  week_label STRING,                       -- "Week 39, 2025"

  -- Period calculations
  business_days_in_month INT64,
  days_since_month_start INT64,
  days_until_month_end INT64
)
CLUSTER BY calendar_date
OPTIONS (
  description = "Time dimension optimized for Metabase filtering and fiscal reporting"
);