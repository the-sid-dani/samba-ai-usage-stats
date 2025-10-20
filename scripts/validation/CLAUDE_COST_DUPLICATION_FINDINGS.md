# Claude Cost Duplication Issue - Root Cause Analysis

## Problem Summary

**Dashboard shows**: $162.14 (Oct 3-19, 2025)
**BigQuery shows**: $22,333.38 (Oct 3-17, 2025)
**Discrepancy**: **138x inflation**

## Root Cause Identified

The `claude_cost_report` table contains **DUPLICATE cost data** at two levels:

1. **Organization-level aggregates** (`workspace_id IS NULL`)
2. **Workspace-level breakdowns** (`workspace_id IS NOT NULL`)

When we `SUM(amount_usd)` without filtering, we're counting the same costs multiple times.

### Evidence

For the same day (Oct 7, 2025), same model (Claude Sonnet 4.5), same token type (cache_creation):

| workspace_id | amount_usd |
|--------------|------------|
| `wrkspc_01WtfAtqQsV3zBDs9RYpNZdR` | $305.78 |
| `NULL` (org-level) | $279.10 |

**These represent overlapping costs, not separate charges!**

### Current Query (WRONG)
```sql
SELECT SUM(amount_usd) as total_cost
FROM `ai-workflows-459123.ai_usage_analytics.claude_cost_report`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-10-19'
-- Result: $22,333.38 (INFLATED due to double-counting)
```

### Impact Analysis

| Filter | Total Cost | Note |
|--------|------------|------|
| **No filter (current)** | $22,333.38 | ❌ WRONG - double counts everything |
| **workspace_id IS NOT NULL** | $8,431.46 | Only workspace-specific costs |
| **workspace_id IS NULL** | $13,901.91 | Only org-level aggregates |

Even with deduplication, $8,431 or $13,902 is still **50-85x higher** than dashboard's $162.

## Additional Issues to Investigate

The deduplication fixes the double-counting, but there's still a massive discrepancy:

1. **Date Range Mismatch?**
   - Dashboard: Oct 3-19 (17 days)
   - BigQuery: Oct 3-17 (15 days) - missing Oct 18-19 data

2. **Workspace Filtering?**
   - Dashboard note: "Showing API usage only. Select 'All workspaces' to include workbench usage."
   - Are we missing a filter for API-only vs workbench?

3. **Different Cost Calculation?**
   - Is the dashboard showing a different metric (e.g., only input/output tokens, excluding cache costs)?
   - Need to verify what the dashboard is actually displaying

## Immediate Fixes Required

### 1. Fix All BigQuery Queries

Update all cost queries to use workspace-level data only:

```sql
SELECT SUM(amount_usd) as total_cost
FROM `ai-workflows-459123.ai_usage_analytics.claude_cost_report`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-10-19'
  AND workspace_id IS NOT NULL  -- ← ADD THIS FILTER
```

**OR** use org-level only:

```sql
SELECT SUM(amount_usd) as total_cost
FROM `ai-workflows-459123.ai_usage_analytics.claude_cost_report`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-10-19'
  AND workspace_id IS NULL  -- ← ADD THIS FILTER
```

### 2. Fix Metabase Dashboards

All dashboard cards using `claude_cost_report` need the same filter added.

### 3. Create Deduped View (Recommended)

Create a view that automatically filters to prevent future mistakes:

```sql
CREATE OR REPLACE VIEW `ai-workflows-459123.ai_usage_analytics.vw_claude_cost_deduped` AS
SELECT *
FROM `ai-workflows-459123.ai_usage_analytics.claude_cost_report`
WHERE workspace_id IS NOT NULL  -- or IS NULL, depending on requirements
```

Then use `vw_claude_cost_deduped` instead of `claude_cost_report` in all queries.

### 4. Investigate Ingestion Logic

Need to check `src/ingestion/ingest_claude_costs.py` in the Docker container to understand:
- Why are we ingesting both org-level AND workspace-level data?
- Should we filter during ingestion instead?
- Is this the intended behavior from Anthropic's API?

## Next Steps

1. **Immediate**: Add `workspace_id IS NOT NULL` filter to all validation queries
2. **Verify**: Compare deduped BigQuery results with dashboard - still expect discrepancy
3. **Investigate**: Why is $8,431 (deduped) still 52x higher than $162 (dashboard)?
4. **Possible explanations**:
   - Dashboard filtering by specific workspace/API key
   - Dashboard showing different date range
   - Dashboard excluding certain cost types (cache costs?)
   - Units issue (cents vs dollars?)
   - Multiple organizations being aggregated?

## Testing

Run this query to verify the fix:

```sql
-- Compare before/after deduplication
SELECT
  'BEFORE (with dupes)' as scenario,
  SUM(amount_usd) as total_cost,
  COUNT(*) as record_count
FROM `ai-workflows-459123.ai_usage_analytics.claude_cost_report`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-10-17'

UNION ALL

SELECT
  'AFTER (workspace only)' as scenario,
  SUM(amount_usd) as total_cost,
  COUNT(*) as record_count
FROM `ai-workflows-459123.ai_usage_analytics.claude_cost_report`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-10-17'
  AND workspace_id IS NOT NULL

UNION ALL

SELECT
  'AFTER (org only)' as scenario,
  SUM(amount_usd) as total_cost,
  COUNT(*) as record_count
FROM `ai-workflows-459123.ai_usage_analytics.claude_cost_report`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-10-17'
  AND workspace_id IS NULL
```

Expected results:
- BEFORE: $22,333.38 (❌ wrong)
- AFTER (workspace): $8,431.46 (✓ deduplicated, but still investigate vs $162)
- AFTER (org): $13,901.91 (✓ deduplicated, but still investigate vs $162)

---

**Date**: 2025-10-19
**Severity**: CRITICAL - Cost reporting is 50-138x inflated
**Status**: Root cause identified, fix ready to implement
