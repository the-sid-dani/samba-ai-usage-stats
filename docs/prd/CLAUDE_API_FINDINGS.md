# Claude API Documentation vs Actual Implementation - Gap Analysis

## Executive Summary

**Status**: 🔴 **CRITICAL GAPS FOUND** - The documentation describes a significantly different system than what was implemented.

**Key Finding**: The PRD/Architecture docs describe a well-structured approach with proper data segmentation, but the actual implementation appears to have deviated significantly, resulting in:
- 34-138x cost inflation
- Missing platform segmentation
- Data duplication at multiple levels
- No filtering for API-only usage

---

## What the Documentation Says (PLANNED)

### Table Structure (from `data-architecture.md`)

The PRD specifies **3 separate Claude tables**:

#### 1. `claude_usage_stats`
- **Purpose**: Claude.ai chat/web interface usage ONLY
- **Source**: Manual upload via Google Sheets
- **Update**: Manual (weekly/monthly)
- **NOT automated**

#### 2. `claude_code_usage_stats`
- **Purpose**: Claude Code IDE metrics
- **Source**: Claude Admin API `/claude_code` endpoint
- **Fields**: `user_email`, `commits`, `lines_added`, `estimated_cost_usd`, `input_tokens`, `output_tokens`
- **Update**: Daily automated

#### 3. `claude_expenses` ⭐ **THIS IS THE KEY TABLE**
- **Purpose**: ALL Claude platform costs (claude.ai + Claude Code + API)
- **Source**: Claude Admin API Cost Report
- **Critical Feature**: **Platform segmentation field**
  - `platform`: "claude.ai" | "claude_code" | "claude_api"
- **Filtering Logic**:
  ```
  Use workspace_id or API endpoint patterns to distinguish
  claude.ai vs Claude Code vs API usage
  ```

### Additional Table (from `data-architecture.md`)

#### 4. `api_usage_expenses`
- **Purpose**: Claude API programmatic usage costs ONLY
- **Source**: Claude Admin API Cost Report (FILTERED)
- **Filtering Logic**:
  ```
  - Include ONLY programmatic API usage (Messages API, Batch API, Tools API)
  - Exclude Claude Code and claude.ai costs (those go in claude_expenses)
  - Use API key patterns or workspace IDs to filter
  ```

### API Integration Specs (from `external-api-integrations.md`)

**Anthropic Claude API:**
- Base URL: `https://api.anthropic.com/v1`
- Endpoints:
  - `GET /organizations/usage_report/messages` - Token counts and model usage
  - `GET /organizations/cost_report` - Cost breakdown by workspace
- **Key Note**: "API key ID to user email mapping required via Google Sheets"
- **Pagination**: Handle for large date ranges
- **31-day maximum query limit** - requires chunked requests

---

## What Was Actually Implemented (ACTUAL)

### Tables Created (from BigQuery inspection)

1. ✅ `claude_ai_usage_stats` (matches spec)
2. ✅ `claude_code_usage_stats` (matches spec)
3. ❌ `claude_cost_report` (WRONG - should be `claude_expenses`)
4. ✅ `claude_usage_report` (extra table not in spec)
5. ❌ **MISSING**: `api_usage_expenses` table completely absent
6. ❌ **MISSING**: Platform segmentation field

### Critical Deviations

#### Deviation 1: Wrong Table Name & Schema
**Planned**: `claude_expenses` with platform field
**Actual**: `claude_cost_report` WITHOUT platform field

**Impact**: Cannot distinguish claude.ai vs Claude Code vs API costs

#### Deviation 2: No Platform Filtering
**Planned**:
```sql
WHERE platform = 'claude_api'  -- Filter to API-only costs
```

**Actual**:
```sql
-- No filtering - pulls EVERYTHING from org
```

**Impact**: Includes ALL organization usage (dev, staging, prod, all platforms)

#### Deviation 3: Missing `api_usage_expenses` Table
**Planned**: Separate table for programmatic API usage only
**Actual**: Table doesn't exist

**Impact**: Can't track API costs separately from platform costs

#### Deviation 4: Incorrect API Usage
**Planned** (from docs):
```python
# Should use workspace filtering or group_by
GET /cost_report?group_by[]=workspace_id&group_by[]=description
```

**Actual** (from testing):
```python
# Appears to NOT use group_by
# Stores both org-level AND workspace-level data
# Results in double-counting
```

#### Deviation 5: Data Duplication
**Planned**: Single source of truth per cost
**Actual**:
- Org-level data (`workspace_id = NULL`): $13,902
- Workspace-level data (`workspace_id = 'wrkspc_...'`): $8,431
- **Combined (wrong)**: $22,333

---

## Documented Requirements vs Implementation

| Requirement | Doc Reference | Status | Gap |
|------------|---------------|---------|-----|
| **FR4: Platform segmentation** | requirements.md:FR4 | ❌ MISSING | No `platform` field in schema |
| **FR6: API-only cost tracking** | requirements.md:FR6 | ❌ MISSING | `api_usage_expenses` table not created |
| **Cost reconciliation** | requirements.md:FR10 | ❌ FAILED | Costs 34-138x inflated vs vendor dashboard |
| **Workspace filtering** | data-architecture.md:76-78 | ❌ NOT IMPLEMENTED | Pulling all org data |
| **API key mapping** | data-architecture.md:147-158 | ⚠️ PARTIAL | `dim_api_keys` exists but not being used correctly |

---

## Root Cause Analysis

### Why the Deviation Happened

Based on the evidence, here's what likely occurred:

1. **Implementation rushed or incomplete**
   - Skipped platform segmentation logic
   - Didn't implement filtering by workspace_id
   - Created generic `claude_cost_report` instead of properly named `claude_expenses`

2. **API misunderstood**
   - Didn't use `group_by[]` parameter correctly
   - Pulled org-wide data without filtering
   - Stored both org and workspace levels causing duplication

3. **No validation against spec**
   - If cost validation had been done against dashboard, 34x inflation would have been caught
   - No data quality checks implemented (FR10 violated)

4. **Missing `api_usage_expenses` implementation**
   - Entire table/workflow never built
   - Can't distinguish API usage from platform usage

---

## What the Correct Implementation Should Look Like

### Table 1: `claude_expenses` (rename from `claude_cost_report`)

```sql
CREATE TABLE `ai_usage_analytics.claude_expenses` (
  expense_date DATE NOT NULL,
  platform STRING NOT NULL,  -- ⭐ CRITICAL: "claude.ai" | "claude_code" | "claude_api"
  workspace_id STRING,
  api_key_id STRING,
  model STRING,
  cost_usd NUMERIC(10,4) NOT NULL,
  cost_type STRING,  -- "tokens" | "subscription" | "other"
  token_type STRING,  -- "input" | "output" | "cache_read"
  service_tier STRING,
  description STRING,
  currency STRING,
  ingestion_timestamp TIMESTAMP NOT NULL
)
PARTITION BY expense_date
CLUSTER BY platform, workspace_id, model;
```

### Table 2: `api_usage_expenses` (NEW - currently missing)

```sql
CREATE TABLE `ai_usage_analytics.api_usage_expenses` (
  expense_date DATE NOT NULL,
  api_key_id STRING NOT NULL,
  model STRING NOT NULL,
  cost_usd NUMERIC(10,4) NOT NULL,
  input_tokens INT64,
  output_tokens INT64,
  cache_tokens INT64,
  endpoint STRING,  -- "messages" | "batch" | "tools"
  service_tier STRING,
  ingestion_timestamp TIMESTAMP NOT NULL
)
PARTITION BY expense_date
CLUSTER BY api_key_id, model;
```

### Correct Ingestion Logic

```python
def ingest_claude_costs(start_date, end_date):
    """
    Fetch Claude costs with proper filtering and platform attribution
    """
    # Fetch with group_by to get detailed breakdown
    params = {
        "starting_at": start_date,
        "ending_at": end_date,
        "group_by[]": ["workspace_id", "description"]
    }

    response = api_client.get("/organizations/cost_report", params=params)

    for day in response['data']:
        for record in day['results']:
            # Platform attribution logic
            platform = determine_platform(
                workspace_id=record['workspace_id'],
                api_key_id=record.get('api_key_id'),
                description=record['description']
            )

            # Insert into claude_expenses
            if platform in ['claude.ai', 'claude_code']:
                insert_to_claude_expenses(record, platform)

            # Insert into api_usage_expenses (if API usage)
            elif platform == 'claude_api':
                insert_to_api_usage_expenses(record)


def determine_platform(workspace_id, api_key_id, description):
    """
    Logic to determine platform from API response
    """
    # CRITICAL: This logic needs to be defined based on:
    # - Workspace ID patterns
    # - API key patterns
    # - Description field content
    # - Service tier information

    if workspace_id == 'wrkspc_01WtfAtqQsV3zBDs9RYpNZdR':
        return 'claude_code'  # Example - verify actual workspace mapping
    elif api_key_id and api_key_id.startswith('apikey_'):
        return 'claude_api'
    else:
        return 'claude.ai'
```

---

## Critical Questions That Need Answers

1. **Workspace Mapping**:
   - What workspace_id represents Claude Code?
   - What workspace_id represents claude.ai?
   - What represents API-only usage?

2. **Current Dashboard**:
   - The dashboard showing $162-$246 - what filters is it using?
   - Which workspace is it viewing?
   - Is it filtering to "API usage only" explicitly?

3. **Data Source**:
   - Are we pulling from correct organization ID?
   - Are there multiple organizations in the same account?
   - Could there be test/staging data included?

4. **API Key Attribution**:
   - What API keys belong to which platform?
   - Is there a mapping table we should be using?
   - Are we joining to `dim_api_keys` table correctly?

---

## Recommended Fix Approach

### Option 1: Quick Fix (Keep Current Tables)
1. Add `platform` column to `claude_cost_report`
2. Backfill platform attribution using workspace_id logic
3. Filter queries to specific platform/workspace
4. Still has duplication issue

**Time**: 2-3 hours
**Risk**: Medium - data still fundamentally wrong

### Option 2: Rebuild Per Spec (RECOMMENDED)
1. Drop all Claude cost tables
2. Create `claude_expenses` with platform field
3. Create `api_usage_expenses` table
4. Implement correct ingestion with filtering
5. Backfill clean data

**Time**: 4-6 hours
**Risk**: Low - follows documented spec

### Option 3: Hybrid Approach
1. Keep `claude_cost_report` but fix ingestion
2. Add platform attribution
3. Remove duplicate org/workspace storage
4. Don't create `api_usage_expenses` (defer to later)

**Time**: 3-4 hours
**Risk**: Medium - partial compliance with spec

---

## Next Steps

1. **Immediate**: Determine workspace → platform mapping
2. **Immediate**: Identify which workspace the dashboard is viewing
3. **Decision**: Choose fix approach (recommend Option 2)
4. **Implementation**: Rebuild with correct spec
5. **Validation**: Verify totals match dashboard before full backfill

---

**Document Status**: Gap analysis complete
**Created**: 2025-10-19
**Severity**: CRITICAL - Implementation does not match documented architecture
**Recommendation**: Rebuild per specification (Option 2)
