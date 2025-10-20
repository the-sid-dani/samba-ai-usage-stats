# Claude API - Unified Table Design Analysis

## Executive Summary

**Question**: Can we create ONE giant table from Claude API covering all financial data, keys, costs, and tokens?

**Answer**: **YES, but with trade-offs.** I recommend **ONE table for costs** + lightweight views, not everything in one table.

---

## What the API Actually Returns

### Endpoint 1: `/cost_report` (with group_by)
**Returns**: Detailed cost breakdown by token type
```json
{
  "workspace_id": "wrkspc_xxx" or null,
  "model": "claude-sonnet-4-5-20250929",
  "token_type": "cache_creation.ephemeral_5m_input_tokens",  ← GRANULAR
  "amount": "94.662",
  "cost_type": "tokens",
  "description": "Claude Sonnet 4.5 Usage - Input Tokens, Cache Write",
  "service_tier": "standard",
  "context_window": "0-200k"
}
```

**Key Insight**:
- ✅ Has costs
- ✅ Has model
- ✅ Has workspace_id
- ❌ NO api_key_id
- ❌ NO token counts
- 🔑 **One record PER token type** (input, output, cache_read, cache_write)

### Endpoint 2: `/usage_report/messages` (with group_by)
**Returns**: Aggregated token usage
```json
{
  "api_key_id": "apikey_013H8hcx57uSm6gt3ytidGwz",  ← HAS API KEY!
  "workspace_id": "wrkspc_xxx",
  "model": "claude-sonnet-4-5-20250929",
  "uncached_input_tokens": 12446,  ← AGGREGATED
  "output_tokens": 19314,
  "cache_read_input_tokens": 5566,
  "cache_creation": {
    "ephemeral_5m_input_tokens": 21024
  },
  "server_tool_use": {
    "web_search_requests": 0
  }
}
```

**Key Insight**:
- ✅ Has token counts
- ✅ Has api_key_id (ONLY endpoint with this!)
- ✅ Has workspace_id
- ✅ Has model
- ❌ NO costs
- 🔑 **One record PER model** (all token types aggregated)

### Endpoint 3: `/usage_report/claude_code`
**Returns**: Claude Code IDE metrics
```json
{
  "organization_id": "xxx",
  "actor_type": "user_actor" or "api_actor",
  "user_email": "user@example.com",  ← HAS EMAIL!
  "terminal_type": "cursor",
  "num_sessions": 5,
  "lines_added": 1234,
  "commits_by_claude_code": 3,
  "total_input_tokens": 50000,
  "total_estimated_cost_usd": 15.25  ← HAS COST!
}
```

**Key Insight**:
- ✅ Has token counts
- ✅ Has estimated costs
- ✅ Has user_email (ONLY endpoint with this!)
- ✅ Has IDE-specific metrics
- ❌ NO workspace_id
- ❌ Different data model entirely

---

## The Join Problem

**Cost Report**: 20 records for Oct 3
- 1 record for claude-sonnet-4-5 / uncached_input_tokens / $3.73
- 1 record for claude-sonnet-4-5 / output_tokens / $28.97
- 1 record for claude-sonnet-4-5 / cache_read / $73.98
- 1 record for claude-sonnet-4-5 / cache_creation / $94.66

**Usage Report**: 1 record for Oct 3
- 1 record for claude-sonnet-4-5 / 12k input tokens, 19k output tokens (aggregated)

**Result**: **Cannot JOIN 1:1** because granularity is different!

---

## 🎯 Recommended Solution

### ✅ OPTION 1: ONE Cost Table + Views (BEST)

**Create ONE primary table from Cost Report** (has everything we need):

```sql
CREATE TABLE `claude_costs` (
  -- Dimensions
  activity_date DATE NOT NULL,
  organization_id STRING NOT NULL,
  workspace_id STRING,  -- Can be NULL for org-wide
  model STRING NOT NULL,

  -- Cost breakdown
  token_type STRING NOT NULL,  -- 'uncached_input', 'output', 'cache_read', etc.
  cost_type STRING NOT NULL,   -- 'tokens', 'web_search'
  amount_usd NUMERIC(12,6) NOT NULL,
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

**Then create VIEW for aggregated view**:

```sql
CREATE VIEW `claude_daily_summary` AS
SELECT
  activity_date,
  workspace_id,
  model,
  -- Aggregate costs by type
  SUM(CASE WHEN token_type LIKE '%input%' AND token_type NOT LIKE '%cache%'
      THEN amount_usd ELSE 0 END) AS input_cost_usd,
  SUM(CASE WHEN token_type = 'output_tokens'
      THEN amount_usd ELSE 0 END) AS output_cost_usd,
  SUM(CASE WHEN token_type LIKE '%cache_read%'
      THEN amount_usd ELSE 0 END) AS cache_read_cost_usd,
  SUM(CASE WHEN token_type LIKE '%cache_creation%'
      THEN amount_usd ELSE 0 END) AS cache_write_cost_usd,
  SUM(amount_usd) AS total_cost_usd
FROM `claude_costs`
GROUP BY activity_date, workspace_id, model;
```

**Optionally add separate lightweight table for API key mapping**:

```sql
CREATE TABLE `claude_usage_tokens` (
  activity_date DATE NOT NULL,
  api_key_id STRING NOT NULL,  -- ← ONLY way to get API keys!
  workspace_id STRING,
  model STRING NOT NULL,

  uncached_input_tokens INT64,
  output_tokens INT64,
  cache_read_input_tokens INT64,
  cache_creation_5m_tokens INT64,
  cache_creation_1h_tokens INT64,
  web_search_requests INT64,

  ingestion_timestamp TIMESTAMP NOT NULL
)
PARTITION BY activity_date
CLUSTER BY api_key_id, workspace_id;
```

**Benefits**:
- ✅ Cost data is complete and granular
- ✅ Can filter by workspace (solves our $162 vs $22k problem!)
- ✅ Can aggregate however needed via views
- ✅ Separate api_key mapping if needed
- ✅ Small, focused tables = fast queries
- ✅ ONE ingestion job for costs (primary data)
- ✅ ONE optional job for api_key mapping

**Drawbacks**:
- Need to JOIN if you want api_key_id with costs (but that's rare)

---

### ⚠️ OPTION 2: ONE Giant Wide Table (NOT RECOMMENDED)

```sql
CREATE TABLE `claude_unified` (
  activity_date DATE NOT NULL,
  record_source STRING NOT NULL,  -- 'cost_report' or 'usage_report' or 'claude_code'

  -- Common fields
  workspace_id STRING,
  model STRING,

  -- From cost_report (NULL for usage records)
  token_type STRING,
  amount_usd NUMERIC(12,6),
  cost_type STRING,
  description STRING,

  -- From usage_report (NULL for cost records)
  api_key_id STRING,
  uncached_input_tokens INT64,
  output_tokens INT64,
  cache_read_tokens INT64,

  -- From claude_code (NULL for others)
  user_email STRING,
  terminal_type STRING,
  num_sessions INT64,
  lines_added INT64
)
PARTITION BY activity_date;
```

**Drawbacks**:
- ❌ Lots of NULL values (50%+ of columns NULL per row)
- ❌ Confusing to query (which fields are valid when?)
- ❌ Larger storage footprint
- ❌ Slower queries (more columns to scan)
- ❌ Harder to maintain

**Benefits**:
- ✅ Everything in one place
- ✅ ONE ingestion job

---

## 💡 My Recommendation: Simplified 2-Table Approach

### Table 1: `claude_costs` (PRIMARY - 80% of your needs)

**Source**: `/cost_report` with `group_by[]=workspace_id&group_by[]=description`

**One ingestion job**, stores:
- All costs broken down by token type
- Workspace attribution
- Model information
- Everything needed for financial reporting

**This solves your current problem**:
- Filter by workspace_id to get accurate costs
- No more 34x inflation
- Matches dashboard

### Table 2: `claude_api_keys` (OPTIONAL - if you need API key attribution)

**Source**: `/usage_report/messages` with `group_by[]=api_key_id`

**Lightweight table** just for API key → usage mapping:
- Links api_key_id to costs via workspace_id
- Token counts if needed
- Only create if you actually need API-level attribution

### Table 3: `claude_code_stats` (SEPARATE - different data model)

**Source**: `/usage_report/claude_code`

**Keep separate** because:
- Different actor model (user_email vs api_key)
- IDE-specific metrics
- Already has costs included
- Doesn't overlap with cost/usage reports

---

## 🎯 Immediate Action Plan

### Step 1: Create ONE table for costs (15 min)

```sql
CREATE TABLE `ai_usage_analytics.claude_costs` (
  activity_date DATE NOT NULL,
  organization_id STRING NOT NULL,
  workspace_id STRING,
  model STRING NOT NULL,
  token_type STRING NOT NULL,
  cost_type STRING NOT NULL,
  amount_usd NUMERIC(12,6) NOT NULL,
  currency STRING NOT NULL,
  description STRING,
  service_tier STRING,
  context_window STRING,
  ingestion_timestamp TIMESTAMP NOT NULL
)
PARTITION BY activity_date
CLUSTER BY workspace_id, model, token_type;
```

### Step 2: Create ONE ingestion script (30 min)

```python
def ingest_claude_costs(date):
    """Single job to fetch and load ALL cost data"""
    params = {
        "starting_at": date,
        "ending_at": date,
        "group_by[]": ["workspace_id", "description"]
    }

    response = api.get("/organizations/cost_report", params=params)

    # Transform and load - simple!
    for day in response['data']:
        for record in day['results']:
            insert_to_bigquery(
                activity_date=day['starting_at'],
                organization_id=ORG_ID,
                workspace_id=record['workspace_id'],
                model=record['model'],
                token_type=record['token_type'],
                cost_type=record['cost_type'],
                amount_usd=float(record['amount']),
                currency=record['currency'],
                description=record['description'],
                service_tier=record['service_tier'],
                context_window=record['context_window']
            )
```

### Step 3: Add workspace filter for your dashboard (5 min)

```sql
-- Your dashboard query
SELECT
  activity_date,
  model,
  SUM(amount_usd) as daily_cost
FROM `claude_costs`
WHERE workspace_id = 'wrkspc_01WtfAtqQsV3zBDs9RYpNZdR'  -- Filter to your workspace
  AND activity_date BETWEEN '2025-10-03' AND '2025-10-19'
GROUP BY activity_date, model;
```

### Step 4: Validate (10 min)

```sql
-- Should match dashboard ($162-$246)
SELECT SUM(amount_usd)
FROM `claude_costs`
WHERE workspace_id = 'wrkspc_01WtfAtqQsV3zBDs9RYpNZdR'
  AND activity_date BETWEEN '2025-10-03' AND '2025-10-19';
```

---

## Summary Table

| Approach | Tables | Jobs | Storage | Query Speed | Complexity |
|----------|--------|------|---------|-------------|------------|
| **ONE cost table (recommended)** | 1 | 1 | Small | Fast | Simple |
| **Cost + API keys** | 2 | 2 | Small | Fast | Medium |
| **ONE giant table** | 1 | 1 | Large | Slow | High |
| **Separate tables (current broken)** | 3+ | 3+ | Medium | Medium | High |

---

## Bottom Line

**YES, you can create ONE table** for Claude financial data!

**Recommended**:
- ✅ ONE `claude_costs` table from `/cost_report`
- ✅ ONE ingestion job
- ✅ Simple, fast, solves your problem
- ✅ Add workspace filtering to get accurate costs
- ✅ Optionally add `claude_api_keys` table if you need API-level attribution

**This gives you**:
- All costs broken down by token type
- Workspace attribution (solve the $162 vs $22k issue)
- Model information
- Everything for financial dashboards
- ONE simple ingestion pipeline

Would you like me to write the complete ingestion script now?
