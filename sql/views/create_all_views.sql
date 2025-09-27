-- Create All Analytics Views
-- Script to create all analytics views for Looker Studio integration
-- Run this after fact tables are populated with data

-- Set project and dataset variables (replace with actual values)
-- DECLARE project_id STRING DEFAULT 'your-project-id';
-- DECLARE dataset STRING DEFAULT 'ai_usage_analytics';

-- Create Monthly Finance Summary View
-- Provides cost aggregations by platform, user, and month
SOURCE sql/views/vw_monthly_finance.sql;

-- Create Productivity Metrics View
-- Engineering productivity analytics with acceptance rates and trends
SOURCE sql/views/vw_productivity_metrics.sql;

-- Create Cost Allocation Workbench View
-- ROI analysis and cost allocation for team/project reporting
SOURCE sql/views/vw_cost_allocation.sql;

-- Create Executive Summary View
-- High-level KPIs for executive dashboard
SOURCE sql/views/vw_executive_summary.sql;

-- Grant permissions for Looker Studio service account
-- (Replace with actual service account email)
-- GRANT `roles/bigquery.dataViewer` ON TABLE `${project_id}.${dataset}.vw_monthly_finance` TO 'serviceAccount:looker-studio@your-project.iam.gserviceaccount.com';
-- GRANT `roles/bigquery.dataViewer` ON TABLE `${project_id}.${dataset}.vw_productivity_metrics` TO 'serviceAccount:looker-studio@your-project.iam.gserviceaccount.com';
-- GRANT `roles/bigquery.dataViewer` ON TABLE `${project_id}.${dataset}.vw_cost_allocation` TO 'serviceAccount:looker-studio@your-project.iam.gserviceaccount.com';
-- GRANT `roles/bigquery.dataViewer` ON TABLE `${project_id}.${dataset}.vw_executive_summary` TO 'serviceAccount:looker-studio@your-project.iam.gserviceaccount.com';