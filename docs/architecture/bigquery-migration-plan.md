# 🚨 **BIGQUERY MIGRATION PLAN**

## **BREAKING CHANGE: Complete Table Rebuild Required**

The new platform categorization architecture requires **dropping all existing BigQuery tables** and rebuilding with optimized schemas. This is necessary because:

1. **Platform Detection**: Current tables lack proper `platform` field for category separation
2. **Schema Optimization**: New tables are optimized for platform-specific metrics
3. **Attribution Enhancement**: Enhanced attribution confidence and multi-method support
4. **Performance Optimization**: Improved partitioning and clustering strategies

## **Migration Timeline**

### **Phase 1: Parallel Deployment (Week 1)**
```sql
-- 1. Create new tables alongside existing ones
CREATE TABLE fact_cursor_daily_usage_v2 (...);
CREATE TABLE fact_claude_daily_usage_v2 (...);

-- 2. Deploy dual-write pipeline
-- Populate both old and new schemas during transition

-- 3. Create new analytical views
CREATE VIEW vw_ai_coding_productivity_v2 (...);
```

### **Phase 2: Validation (Week 2)**
```sql
-- Validate data consistency between old and new schemas
WITH validation_check AS (
  SELECT
    COUNT(*) as old_count FROM raw_cursor_usage
  UNION ALL
  SELECT
    COUNT(*) as new_count FROM fact_cursor_daily_usage_v2
)
SELECT * FROM validation_check;
```

### **Phase 3: Cutover (Week 3)**
```sql
-- 🚨 DROP EXISTING TABLES (Point of no return)
DROP TABLE IF EXISTS raw_cursor_usage;
DROP TABLE IF EXISTS raw_anthropic_usage;
DROP TABLE IF EXISTS raw_anthropic_cost;
DROP TABLE IF EXISTS fct_usage_daily;
DROP TABLE IF EXISTS fct_cost_daily;
DROP TABLE IF EXISTS dim_users;
DROP TABLE IF EXISTS dim_api_keys;

-- Rename new tables to production names
ALTER TABLE fact_cursor_daily_usage_v2 RENAME TO fact_cursor_daily_usage;
ALTER TABLE fact_claude_daily_usage_v2 RENAME TO fact_claude_daily_usage;

-- Update all views to point to new tables
CREATE OR REPLACE VIEW vw_ai_coding_productivity AS (...);
```

## **Data Preservation Strategy**
- **Historical Data**: Export existing data before migration for validation
- **Backup Tables**: Keep archived copies for 30 days post-migration
- **Rollback Plan**: Maintain ability to restore old schema if needed

---
