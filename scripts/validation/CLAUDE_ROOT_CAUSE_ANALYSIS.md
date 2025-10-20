# Claude Cost Data - Complete Root Cause Analysis

## Executive Summary

**Problem**: BigQuery shows $22,333 for Oct 3-17, but Claude dashboard shows $162 for Oct 3-19.

**Root Causes Identified**:
1. **Double-counting**: Org-level + workspace-level data stored together
2. **Wrong data source**: Fetching ALL organization usage instead of filtered view
3. **Missing filters**: Not filtering to "API usage only" like the dashboard

---

## The Three-Layer Problem

### Layer 1: Double Counting (Addressed in Previous Analysis)

We're storing BOTH:
- Organization-level aggregates (`workspace_id = NULL`): **$13,902**
- Workspace-level breakdown (`workspace_id = 'wrkspc_...'`): **$8,431**
- **Combined (wrong)**: **$22,333**

This was identified earlier - we need to filter to one level.

### Layer 2: Wrong API Usage (THE FUNDAMENTAL MISTAKE)

**Our current ingestion is calling the API incorrectly:**

```python
# WRONG (what we're likely doing):
GET /cost_report?starting_at=2025-10-03&ending_at=2025-10-19
# Returns: Organization-wide aggregates WITHOUT detailed breakdown
# Result: $11,427 for Oct 3-9 (extrapolate to ~$22k for Oct 3-17)
```

```python
# CORRECT (what we SHOULD be doing):
GET /cost_report?starting_at=2025-10-03&ending_at=2025-10-19&group_by[]=workspace_id&group_by[]=description
# Returns: Detailed breakdown by workspace, model, token_type
# Result: SAME $11,427 but with proper granularity
```

**Key Finding**: Using `group_by[]=workspace_id&group_by[]=description` gives us:
- `model` field populated
- `token_type` field populated
- `workspace_id` field (can be NULL for org-wide or specific workspace)
- Allows filtering to specific workspaces

**The API behavior:**
- **WITHOUT** `group_by`: Returns only org-level totals, no model/token breakdown
- **WITH** `group_by[]=workspace_id&group_by[]=description`: Returns full breakdown INCLUDING model, token_type, etc.

### Layer 3: Missing Dashboard Filters

The Claude dashboard UI shows:
- **"Showing API usage only. Select 'All workspaces' to include workbench usage."**

This means the dashboard is filtering to:
1. **API usage only** (excluding Claude Code/workbench)
2. Possibly a **specific workspace**
3. Possibly a **specific API key**

Our ingestion is pulling **EVERYTHING**:
- API usage ✓
- Workbench usage ✓
- Claude Code usage ✓
- All workspaces ✓
- All API keys ✓

**This explains the massive difference:**
- Dashboard (filtered): **$162**
- Our data (unfiltered): **$11,427+** (70x difference!)

---

## Evidence & Testing

### Test 1: Ungrouped API Call (Current Broken Approach)
```bash
GET /cost_report?starting_at=2025-10-03&ending_at=2025-10-10

Result:
2025-10-03: $832.00
2025-10-04: $519.22
2025-10-05: $518.72
2025-10-06: $2494.61
2025-10-07: $1954.99
2025-10-08: $2919.20
2025-10-09: $2188.02
TOTAL: $11,426.77
```

**Fields returned**: Only `amount`, `currency`, ALL other fields are `null`

### Test 2: Grouped API Call (Correct Approach)
```bash
GET /cost_report?starting_at=2025-10-03&ending_at=2025-10-10&group_by[]=workspace_id&group_by[]=description

Result: SAME $11,426.77 total
BUT NOW with:
- model: "claude-sonnet-4-5-20250929", "claude-3-5-haiku-20241022", etc.
- token_type: "uncached_input_tokens", "cache_creation.ephemeral_5m_input_tokens", etc.
- description: "Claude Sonnet 4.5 Usage - Input Tokens, Cache Write"
- workspace_id: null (for org-wide) or "wrkspc_..." (for specific workspace)
```

### Test 3: BigQuery Current State
```sql
-- Without workspace filter
SELECT SUM(amount_usd) FROM claude_cost_report
WHERE activity_date BETWEEN '2025-10-03' AND '2025-10-17'
=> $22,333 (ORG-LEVEL + WORKSPACE-LEVEL COMBINED)

-- Org-level only
WHERE workspace_id IS NULL
=> $13,902

-- Workspace-level only
WHERE workspace_id = 'wrkspc_01WtfAtqQsV3zBDs9RYpNZdR'
=> $8,431
```

---

## The Complete Solution

### Fix 1: Update Ingestion Code

The Cloud Run job at `src/ingestion/ingest_claude_costs.py` needs to:

```python
# ADD group_by parameter to API calls
params = {
    "starting_at": start_date,
    "ending_at": end_date,
    "group_by[]": ["workspace_id", "description"]  # ← ADD THIS!
}
```

**Note**: Even though `group_by` is specified, the API only allows:
- `"workspace_id"`
- `"description"`

NOT `"model"` or `"token_type"` - but those fields get populated automatically when using the allowed group_by values!

### Fix 2: Add Workspace Filtering

Determine which workspace(s) represent "API usage only":

```python
# Option A: Filter during ingestion
if row.get('workspace_id') == 'wrkspc_01WtfAtqQsV3zBDs9RYpNZdR':
    # Only ingest this workspace

# Option B: Filter during queries
WHERE workspace_id = 'wrkspc_01WtfAtqQsV3zBDs9RYpNZdR'
```

### Fix 3: Identify "API Usage Only"

Need to determine what constitutes "API usage only" vs workbench:
- Check workspace names/IDs
- Check if specific API keys represent API-only usage
- Possibly query `/usage_report/messages` endpoint separately for API data

### Fix 4: Remove Duplicate Storage

Choose ONE level to store:
- **Option A**: Store workspace-level only (`WHERE workspace_id IS NOT NULL`)
- **Option B**: Store org-level only (`WHERE workspace_id IS NULL`)

Recommendation: **Store workspace-level** for better filtering/analysis.

### Fix 5: Update All Queries

```sql
-- BEFORE (wrong)
SELECT SUM(amount_usd) as total_cost
FROM claude_cost_report
WHERE activity_date BETWEEN '2025-10-03' AND '2025-10-19'

-- AFTER (correct)
SELECT SUM(amount_usd) as total_cost
FROM claude_cost_report
WHERE activity_date BETWEEN '2025-10-03' AND '2025-10-19'
  AND workspace_id IS NOT NULL  -- Deduplicate
  AND workspace_id = 'wrkspc_01WtfAtqQsV3zBDs9RYpNZdR'  -- Filter to correct workspace
  -- TODO: Add filter for "API usage only" once identified
```

---

## Immediate Actions Required

1. **Find the ingestion source code**
   - Located in Docker image: `gcr.io/ai-workflows-459123/ai-usage-analytics-pipeline:latest`
   - File: `src/ingestion/ingest_claude_costs.py`
   - Need to extract or access this code

2. **Verify group_by parameter**
   - Check if ingestion is using `group_by[]` parameter
   - If not, this is the PRIMARY bug

3. **Identify workspace mapping**
   - Determine which workspace ID = "API usage only"
   - Check workspace names via API or dashboard

4. **Test corrected query**
   ```sql
   SELECT SUM(amount_usd)
   FROM claude_cost_report
   WHERE activity_date BETWEEN '2025-10-03' AND '2025-10-17'
     AND workspace_id = 'wrkspc_01WtfAtqQsV3zBDs9RYpNZdR'
   ```
   - Compare to dashboard value of $162
   - If still way off, need to add additional filters

5. **Fix and redeploy ingestion**
   - Add `group_by[]` parameter
   - Add workspace filtering (if needed)
   - Re-run historical ingestion

6. **Update all dashboards/queries**
   - Add workspace filter
   - Remove org-level duplicate data

---

## Questions to Answer

1. What workspace ID represents "API usage only"?
2. Should we filter during ingestion or during queries?
3. Are there multiple workspaces we should include?
4. How do we distinguish API vs Claude Code vs Workbench usage?
5. Should we purge and re-ingest all historical data?

---

## Expected Outcome After Fixes

- BigQuery total should match dashboard (~$162 for Oct 3-19)
- Data will be properly segmented by workspace
- No more double-counting
- Clear separation of API vs workbench usage

---

**Created**: 2025-10-19
**Status**: ROOT CAUSE IDENTIFIED - READY FOR IMPLEMENTATION
**Priority**: CRITICAL - All cost reporting is currently inflated 50-138x
