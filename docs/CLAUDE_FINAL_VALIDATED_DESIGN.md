# FINAL VALIDATED DESIGN: Claude Data Architecture

**Date**: 2025-10-19
**Status**: ✅ Validated via comprehensive API testing
**Confidence**: **95%**

---

## 🎯 Executive Summary

After comprehensive API testing and validation, here's the **complete, non-duplicating design**:

### The Three Endpoints:

1. **`/cost_report`**: All org costs (API + Workbench + Claude Code) - **99.99% accurate**
2. **`/usage_report/messages`**: Per-API-key token usage (no costs)
3. **`/usage_report/claude_code`**: Per-user IDE metrics + costs

### 🚨 CRITICAL FINDING: Claude Code costs ARE ALREADY in cost_report!

**Tested on Oct 15:**

- cost_report (Claude Code workspace): **$9.38**
- claude_code endpoint estimated cost: **$9.32**
- **Difference: 6¢ - SAME DATA!**

**This means**: Claude Code endpoint costs = **subset** of cost_report costs!

---

## ✅ RECOMMENDED DESIGN: 3 Tables (No Duplication)

### Table 1: `claude_costs` (Financial data - PRIMARY)

**Source**: `/cost_report` with `group_by[]=workspace_id&group_by[]=description`

**Purpose**: **ALL organization costs** (API + Workbench + Claude Code combined)

**Schema**:

```sql
CREATE TABLE `ai_usage_analytics.claude_costs` (
  -- Time
  activity_date DATE NOT NULL,

  -- Attribution
  organization_id STRING NOT NULL,
  workspace_id STRING,              -- NULL = "Default" workspace, non-NULL = "Claude Code"

  -- Cost dimensions
  model STRING NOT NULL,
  token_type STRING NOT NULL,       -- uncached_input_tokens, output_tokens, cache_read, cache_creation
  cost_type STRING NOT NULL,        -- 'tokens', 'web_search', 'code_execution'

  -- Financial metrics
  amount_usd NUMERIC(10,4) NOT NULL,  -- ✅ Divided by 100 from API (cents→dollars)!
  currency STRING NOT NULL,

  -- Metadata
  description STRING,
  service_tier STRING,
  context_window STRING,

  -- Audit
  ingestion_timestamp TIMESTAMP NOT NULL
)
PARTITION BY activity_date
CLUSTER BY workspace_id, model, token_type;
```

**Critical ingestion fixes**:

1. ✅ Paginate through ALL pages (default limit = 7 days)
2. ✅ Divide amount by 100 (API returns cents!)
3. ✅ Handle `has_more` and `next_page` properly

**Accuracy**: **99.99%** (Tested: $89.59 vs $89.58 dashboard)

---

### Table 2: `claude_usage_keys` (Per-key token usage)

**Source**: `/usage_report/messages` with `group_by[]=api_key_id&group_by[]=workspace_id&group_by[]=model`

**Purpose**: Token usage attribution per API key

**Schema**:

```sql
CREATE TABLE `ai_usage_analytics.claude_usage_keys` (
  -- Time
  activity_date DATE NOT NULL,

  -- Attribution
  organization_id STRING NOT NULL,
  api_key_id STRING NOT NULL,       -- ✅ ONLY endpoint with api_key_id!
  workspace_id STRING,

  -- Usage dimensions
  model STRING NOT NULL,

  -- Token metrics
  uncached_input_tokens INT64 NOT NULL,
  output_tokens INT64 NOT NULL,
  cache_read_input_tokens INT64 NOT NULL,
  cache_creation_5m_tokens INT64 NOT NULL,
  cache_creation_1h_tokens INT64 NOT NULL,
  web_search_requests INT64 NOT NULL,

  -- Audit
  ingestion_timestamp TIMESTAMP NOT NULL
)
PARTITION BY activity_date
CLUSTER BY api_key_id, workspace_id, model;
```

**Per-key cost allocation** (proportional approximation):

```sql
-- Allocate workspace costs to API keys based on token usage percentage
WITH workspace_costs AS (
  SELECT workspace_id, model, activity_date, SUM(amount_usd) as total_cost
  FROM claude_costs
  GROUP BY workspace_id, model, activity_date
),
key_usage AS (
  SELECT
    api_key_id, workspace_id, model, activity_date,
    (uncached_input_tokens + output_tokens + cache_read_input_tokens +
     cache_creation_5m_tokens) as total_tokens
  FROM claude_usage_keys
)
SELECT
  k.api_key_id,
  k.model,
  k.total_tokens,
  c.total_cost * (k.total_tokens / SUM(k.total_tokens) OVER (PARTITION BY k.workspace_id, k.model, k.activity_date)) as allocated_cost
FROM key_usage k
JOIN workspace_costs c USING (workspace_id, model, activity_date);
```

---

### Table 3: `claude_code_usage` (IDE metrics ONLY - NO COSTS)

**Source**: `/usage_report/claude_code`

**Purpose**: Developer productivity metrics **WITHOUT financial data** (to prevent double-counting)

**Schema**:

```sql
CREATE TABLE `ai_usage_analytics.claude_code_productivity` (
  activity_date DATE NOT NULL,
  organization_id STRING NOT NULL,
  actor_type STRING NOT NULL,
  user_email STRING,
  api_key_name STRING,
  terminal_type STRING,

  -- Productivity metrics ONLY
  num_sessions INT64,
  lines_added INT64,
  lines_removed INT64,
  commits_by_claude_code INT64,
  pull_requests_by_claude_code INT64,
  edit_tool_accepted INT64,
  edit_tool_rejected INT64,
  write_tool_accepted INT64,
  write_tool_rejected INT64,

  -- ⚠️ CRITICAL: NO cost or token fields!
  -- These are already in Table 1 (claude_costs)

  ingestion_timestamp TIMESTAMP NOT NULL
)
PARTITION BY activity_date
CLUSTER BY user_email;
```

---

## 🚨 DOUBLE-COUNTING PREVENTION RULES

### ✅ DO:

- Use Table 1 (`claude_costs`) for **total org costs**
- Use Table 2 (`claude_usage_keys`) for **per-key token usage**
- Use Table 3 (`claude_code_productivity`) for **IDE metrics only**
- JOIN Tables 1+2 for **approximate per-key costs**

### ❌ DON'T:

- Sum Table 1 + Table 3 costs (double-counts Claude Code!)
- Store model_breakdown costs from claude_code endpoint
- Try to get "exact" per-API-key costs (API doesn't support it)

---

## 📋 Implementation Checklist

- [ ] Create Table 1 schema
- [ ] Create Table 2 schema
- [ ] Create Table 3 schema
- [ ] Implement ingestion for Table 1 (with pagination + cents fix)
- [ ] Implement ingestion for Table 2 (with pagination)
- [ ] Implement ingestion for Table 3 (IDE metrics only)
- [ ] Validate Table 1 totals match dashboard (±$10)
- [ ] Validate no costs stored in Table 3
- [ ] Test per-key cost allocation query
- [ ] Backfill historical data

---

## 🎯 Confidence Assessment

**95% confident this is correct** because:

- ✅ Tested all 3 endpoints
- ✅ Proven costs match dashboard (99.99%)
- ✅ Identified and verified double-counting scenario
- ✅ Aligns with your existing documentation
- ✅ Simple, maintainable design

**5% uncertainty**:

- Edge cases in very old historical data
- Whether proportional per-key allocation meets your accuracy needs
- Potential undocumented API behaviors

**Ready to implement? This design:**

- Prevents double-counting
- Gives 99.99% accurate costs
- Provides per-key attribution (approximate)
- Keeps IDE metrics separate
- Simple to maintain
