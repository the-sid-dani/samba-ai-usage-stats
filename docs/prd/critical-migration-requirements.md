# 🚨 **CRITICAL MIGRATION REQUIREMENTS**

## **Breaking Change: Complete Data Model Rebuild**

The updated architecture requires **dropping all existing BigQuery tables** and rebuilding with the new platform categorization design. This is necessary to:

1. **Enable Platform Categorization:** Current tables lack platform detection fields
2. **Optimize Performance:** New schemas have platform-specific clustering and partitioning
3. **Support Enhanced Attribution:** Multi-method attribution with confidence scoring
4. **Enable 4-Dashboard Architecture:** Category-specific views require optimized underlying tables

## **Migration Impact Assessment**

### **📊 Affected Tables (Must be Dropped):**
- `raw_cursor_usage` → replaced with `fact_cursor_daily_usage`
- `raw_anthropic_usage` → replaced with `fact_claude_daily_usage`
- `raw_anthropic_cost` → merged into `fact_claude_daily_usage`
- `fct_usage_daily` → replaced with category-specific fact tables
- `fct_cost_daily` → replaced with category-specific fact tables
- `dim_users` → replaced with `dim_users_enhanced`
- `dim_api_keys` → replaced with `api_key_mappings`

### **📅 Migration Phases:**
- **Phase 1:** Deploy new schema + dual-write pipeline
- **Phase 2:** **BREAKING CHANGE EXECUTION** - Drop old tables, cutover to new schema
- **Phase 3:** Build category-specific Metabase dashboards
- **Phase 4:** Validate business metrics and stakeholder training

### **🎯 Business Continuity Plan:**
- **Data Preservation:** Export existing data for validation and rollback capability
- **Stakeholder Communication:** Notify all dashboard users of upcoming changes
- **Validation Period:** 2-week parallel operation to ensure data consistency
- **Rollback Strategy:** Maintain ability to restore old schema within 30 days

---
