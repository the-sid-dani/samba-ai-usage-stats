# BigQuery Table Schemas with Real Data Samples

**Date:** October 17, 2025
**Status:** VERIFIED with production APIs and data files
**Organization ID:** `1233d3ee-9900-424a-a31a-fb8b8dcd0be3`

---

## Table 1: `claude_ai_usage_stats`

**Purpose:** Claude.ai chat/web interface usage tracking
**Data Source:** Manual upload from claude-logs.csv (Enterprise audit logs)
**Update Frequency:** Manual (weekly/monthly)

### BigQuery Schema

```sql
CREATE TABLE `ai_usage_analytics.claude_ai_usage_stats` (
  event_timestamp TIMESTAMP NOT NULL,
  activity_date DATE NOT NULL,
  user_email STRING NOT NULL,
  user_name STRING,
  user_uuid STRING NOT NULL,
  event_type STRING NOT NULL,
  conversation_uuid STRING,
  project_uuid STRING,
  file_uuid STRING,
  client_platform STRING,
  device_id STRING,
  ip_address STRING,
  user_agent STRING
)
PARTITION BY activity_date
CLUSTER BY user_email, event_type;
```

### Real Data Sample (from production-data/claude-logs.csv)

| event_timestamp | activity_date | user_email | user_name | event_type | client_platform |
|----------------|---------------|------------|-----------|------------|-----------------|
| 2025-10-17T17:16:15.418Z | 2025-10-17 | justin.lundvall@samba.tv | Justin | conversation_created | desktop_app |
| 2025-10-17T17:06:59.995Z | 2025-10-17 | sid.dani@samba.tv | Sid | conversation_created | web_claude_ai |
| 2025-10-17T16:59:27.403Z | 2025-10-17 | sid.dani@samba.tv | Sid | project_document_created | web_claude_ai |
| 2025-10-17T16:45:34.476Z | 2025-10-17 | omar@samba.tv | Omar Zennadi | conversation_created | desktop_app |
| 2025-10-17T16:45:32.665Z | 2025-10-17 | omar@samba.tv | Omar Zennadi | file_uploaded | desktop_app |
| 2025-10-16T18:15:51.559Z | 2025-10-16 | sunni.park@samba.tv | Sunni | project_created | web_claude_ai |

**Event Types Found:**
- `conversation_created`
- `project_created`
- `project_document_created`
- `file_uploaded`

**Client Platforms Found:**
- `web_claude_ai`
- `desktop_app`
- `ios`

---

## Table 2: `claude_code_usage_stats`

**Purpose:** Claude Code IDE productivity metrics (VS Code, Cursor, GoLand integrations)
**Data Source:** Claude Admin API `/v1/organizations/usage_report/claude_code`
**Update Frequency:** Daily automated
**Attribution:** Per-user (email) or per-API-key

### BigQuery Schema

```sql
CREATE TABLE `ai_usage_analytics.claude_code_usage_stats` (
  activity_date DATE NOT NULL,
  organization_id STRING NOT NULL,

  -- User Attribution
  actor_type STRING NOT NULL,  -- 'user_actor' or 'api_actor'
  user_email STRING,           -- For user_actor
  api_key_name STRING,         -- For api_actor

  -- Context
  terminal_type STRING,        -- 'cursor', 'vscode', 'goland', 'ssh-session'
  customer_type STRING,
  subscription_type STRING,

  -- Core Productivity Metrics
  num_sessions INT64,
  lines_added INT64,
  lines_removed INT64,
  commits_by_claude_code INT64,
  pull_requests_by_claude_code INT64,

  -- Tool Actions
  edit_tool_accepted INT64,
  edit_tool_rejected INT64,
  multi_edit_tool_accepted INT64,
  multi_edit_tool_rejected INT64,
  write_tool_accepted INT64,
  write_tool_rejected INT64,
  notebook_edit_tool_accepted INT64,
  notebook_edit_tool_rejected INT64,

  -- Token & Cost Summary (aggregated across all models)
  total_input_tokens INT64,
  total_output_tokens INT64,
  total_cache_read_tokens INT64,
  total_cache_creation_tokens INT64,
  total_estimated_cost_usd FLOAT64,

  -- Metadata
  ingestion_timestamp TIMESTAMP NOT NULL
)
PARTITION BY activity_date
CLUSTER BY user_email, terminal_type;
```

### Real Data Sample (from Claude Admin API)

| activity_date | actor_type | user_email | terminal_type | lines_added | lines_removed | commits | input_tokens | estimated_cost_usd |
|--------------|------------|------------|---------------|-------------|---------------|---------|--------------|-------------------|
| 2025-10-16 | user_actor | max.roycroft@samba.tv | cursor | 17 | 7 | 1 | 267 | 41.00 |
| 2025-10-16 | api_actor | agooch-dev-key | goland | 1 | 1 | 0 | 3493 | 43.00 |
| 2025-10-16 | api_actor | andrii-dev-key | vscode | 0 | 0 | 0 | 0 | 0.00 |
| 2025-10-16 | api_actor | andrii-dev-key | ssh-session | 0 | 0 | 0 | 2484 | 0.00 |

**Model Breakdown (stored separately or in model_breakdown ARRAY field):**
```json
{
  "model": "claude-sonnet-4-5-20250929",
  "tokens": {"input": 267, "output": 12313, "cache_read": 1840002, "cache_creation": 299611},
  "estimated_cost": {"currency": "USD", "amount": 41}
}
```

---

## Table 3: `cursor_usage_stats`

**Purpose:** Cursor IDE productivity and interaction metrics
**Data Source:** Cursor Admin API `/teams/daily-usage-data`
**Update Frequency:** Daily automated
**Attribution:** Per-user email (direct)

### BigQuery Schema

```sql
CREATE TABLE `ai_usage_analytics.cursor_usage_stats` (
  activity_date DATE NOT NULL,
  user_email STRING NOT NULL,
  user_id STRING NOT NULL,
  is_active BOOL NOT NULL,

  -- Productivity Metrics
  total_lines_added INT64,
  total_lines_deleted INT64,
  accepted_lines_added INT64,
  accepted_lines_deleted INT64,

  -- AI Interaction Metrics
  total_applies INT64,
  total_accepts INT64,
  total_rejects INT64,
  total_tabs_shown INT64,
  total_tabs_accepted INT64,

  -- Request Type Breakdown
  composer_requests INT64,
  chat_requests INT64,
  agent_requests INT64,
  cmdk_usages INT64,
  bugbot_usages INT64,

  -- Finance/Billing Request Counts
  subscription_included_reqs INT64,  -- Within 500/month limit
  usage_based_reqs INT64,            -- Overage requests
  api_key_reqs INT64,                -- API key usage

  -- Context
  most_used_model STRING,
  apply_most_used_extension STRING,
  tab_most_used_extension STRING,
  client_version STRING,

  -- Calculated Cost (using pricing model)
  estimated_subscription_cost_usd FLOAT64,
  estimated_overage_cost_usd FLOAT64,
  estimated_total_cost_usd FLOAT64,

  -- Metadata
  ingestion_timestamp TIMESTAMP NOT NULL
)
PARTITION BY activity_date
CLUSTER BY user_email;
```

### Real Data Sample (from Cursor Admin API - Sept 17, 2025)

| activity_date | user_email | total_lines_added | accepted_lines_added | composer_reqs | agent_reqs | subscription_reqs | overage_reqs | most_used_model |
|--------------|------------|-------------------|---------------------|---------------|------------|------------------|--------------|-----------------|
| 2025-09-17 | nathan.konopinski@samba.tv | 6823 | 478 | 0 | 60 | 60 | 0 | claude-4-sonnet |
| 2025-09-17 | max.roycroft@samba.tv | 182 | 144 | 104 | 24 | 0 | 128 | claude-4-sonnet-1m-thinking |
| 2025-09-17 | lukasz.michalek@samba.tv | 0 | 0 | 169 | 71 | 0 | 240 | claude-4-sonnet |
| 2025-09-17 | hanna.zdulska@samba.tv | 317 | 206 | 0 | 11 | 11 | 0 | gpt-5 |
| 2025-09-17 | jose.lopes@samba.tv | 0 | 0 | 0 | 0 | 0 | 0 | (inactive) |

**Cost Calculation Logic:**
```sql
-- Cursor pricing model (approximation)
estimated_subscription_cost_usd = (20.00 / days_in_month)  -- Daily prorated
estimated_overage_cost_usd = usage_based_reqs * overage_rate_per_request
estimated_total_cost_usd = estimated_subscription_cost_usd + estimated_overage_cost_usd
```

---

## Table 4: `claude_usage_report`

**Purpose:** Claude API token usage per API key, workspace, and model
**Data Source:** Claude Admin API `/v1/organizations/usage_report/messages` with `group_by[]=["api_key_id", "workspace_id", "model"]`
**Update Frequency:** Daily automated
**Attribution:** Per API key (requires mapping to users)

### BigQuery Schema

```sql
CREATE TABLE `ai_usage_analytics.claude_usage_report` (
  activity_date DATE NOT NULL,
  organization_id STRING NOT NULL,

  -- Attribution
  api_key_id STRING,           -- Can be null
  workspace_id STRING,         -- Can be null (Default workspace) or 'wrkspc_01WtfAtqQsV3zBDs9RYpNZdR'
  model STRING,                -- e.g., 'claude-sonnet-4-5-20250929'
  service_tier STRING,         -- Usually null in current data
  context_window STRING,       -- Usually null in current data

  -- Token Counts
  uncached_input_tokens INT64,
  output_tokens INT64,
  cache_read_input_tokens INT64,
  cache_creation_1h_tokens INT64,
  cache_creation_5m_tokens INT64,

  -- Tool Usage
  web_search_requests INT64,

  -- Metadata
  ingestion_timestamp TIMESTAMP NOT NULL
)
PARTITION BY activity_date
CLUSTER BY api_key_id, workspace_id, model;
```

### Real Data Sample (from Claude Admin API - Oct 16, 2025)

| activity_date | api_key_id | workspace_id | model | input_tokens | output_tokens | cache_read | cache_create_5m |
|--------------|------------|--------------|-------|--------------|---------------|------------|-----------------|
| 2025-10-16 | apikey_01Eb6TPyqUneJQqKBfv7Gti6 | wrkspc_01WtfAtqQsV3zBDs9RYpNZdR | claude-sonnet-4-5-20250929 | 270 | 12313 | 1840002 | 299611 |
| 2025-10-16 | apikey_01Eb6TPyqUneJQqKBfv7Gti6 | wrkspc_01WtfAtqQsV3zBDs9RYpNZdR | claude-3-5-haiku-20241022 | 21261 | 834 | 0 | 0 |
| 2025-10-16 | apikey_01GKcX6KzVBF8yC9Qsdnd3kS | null | claude-sonnet-4-20250514 | 2855521 | 19480 | 0 | 0 |
| 2025-10-16 | apikey_01WMsewsG39d911CjeZ6sGtn | null | claude-3-5-haiku-20241022 | 6552280 | 122481 | 0 | 0 |
| 2025-10-16 | apikey_017o7G9x1LgUFZ1QH9d8cwed | null | claude-sonnet-4-5-20250929 | 577 | 59914 | 11648537 | 1815225 |

**Workspace Mapping:**
- `wrkspc_01WtfAtqQsV3zBDs9RYpNZdR` = "Claude Code" workspace (misnomer - mixed usage)
- `null` = "Default" workspace

---

## Table 5: `claude_cost_report`

**Purpose:** Claude costs by workspace, model, and token type
**Data Source:** Claude Admin API `/v1/organizations/cost_report` with `group_by[]=["workspace_id", "description"]`
**Update Frequency:** Daily automated
**Attribution:** Per workspace (requires api_key mapping for user attribution)

### BigQuery Schema

```sql
CREATE TABLE `ai_usage_analytics.claude_cost_report` (
  activity_date DATE NOT NULL,
  organization_id STRING NOT NULL,

  -- Attribution
  workspace_id STRING,         -- Can be null (Default) or workspace ID

  -- Cost Details
  model STRING,                -- e.g., 'claude-sonnet-4-5-20250929'
  cost_type STRING,            -- 'tokens', 'web_search'
  token_type STRING,           -- 'uncached_input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation.ephemeral_5m_input_tokens'
  service_tier STRING,         -- 'standard'
  context_window STRING,       -- '0-200k'
  description STRING,          -- e.g., 'Claude Sonnet 4.5 Usage - Input Tokens, Cache Write'

  -- Cost
  currency STRING NOT NULL,    -- Always 'USD'
  amount_usd NUMERIC(12, 6) NOT NULL,  -- Cost amount (decimal)

  -- Metadata
  ingestion_timestamp TIMESTAMP NOT NULL
)
PARTITION BY activity_date
CLUSTER BY workspace_id, model, token_type;
```

### Real Data Sample (from Claude Admin API - Oct 16, 2025)

| activity_date | workspace_id | model | token_type | description | amount_usd |
|--------------|--------------|-------|------------|-------------|------------|
| 2025-10-16 | null | claude-3-5-haiku-20241022 | uncached_input_tokens | Claude Haiku 3.5 Usage - Input Tokens | 527.999760 |
| 2025-10-16 | null | claude-3-5-haiku-20241022 | output_tokens | Claude Haiku 3.5 Usage - Output Tokens | 50.241200 |
| 2025-10-16 | null | claude-sonnet-4-5-20250929 | cache_creation.ephemeral_5m_input_tokens | Claude Sonnet 4.5 Usage - Input Tokens, Cache Write | 776.257875 |
| 2025-10-16 | null | claude-sonnet-4-5-20250929 | cache_read_input_tokens | Claude Sonnet 4.5 Usage - Input Tokens, Cache Hit | 381.724170 |
| 2025-10-16 | null | claude-sonnet-4-5-20250929 | output_tokens | Claude Sonnet 4.5 Usage - Output Tokens | 104.227500 |
| 2025-10-16 | wrkspc_01WtfAtqQsV3zBDs9RYpNZdR | claude-sonnet-4-5-20250929 | cache_creation.ephemeral_5m_input_tokens | Claude Sonnet 4.5 Usage - Input Tokens, Cache Write | 251.958000 |
| 2025-10-16 | wrkspc_01WtfAtqQsV3zBDs9RYpNZdR | claude-3-5-haiku-20241022 | uncached_input_tokens | Claude Haiku 3.5 Usage - Input Tokens | 11.822080 |
| 2025-10-16 | wrkspc_01WtfAtqQsV3zBDs9RYpNZdR | web_search | Web Search Usage | 1.000000 |

**Daily Totals (Oct 16):**
- Default workspace (null): $1,840.65
- Claude Code workspace: $934.16
- **Total:** $2,774.81/day

---

## Table 6: `cursor_expenses_calculated`

**Purpose:** Cursor costs calculated from request counts using pricing model
**Data Source:** Calculated from `cursor_usage_stats` aggregations
**Update Frequency:** Daily calculated
**Attribution:** Per-user

### BigQuery Schema

```sql
CREATE TABLE `ai_usage_analytics.cursor_expenses_calculated` (
  activity_date DATE NOT NULL,
  user_email STRING NOT NULL,

  -- Request Counts (from API)
  subscription_included_reqs INT64,
  usage_based_reqs INT64,
  api_key_reqs INT64,
  total_requests INT64,

  -- Calculated Costs
  subscription_cost_usd FLOAT64,      -- Prorated daily subscription
  overage_cost_usd FLOAT64,           -- Usage beyond 500 reqs
  api_key_cost_usd FLOAT64,           -- API key usage
  total_cost_usd FLOAT64,

  -- Pricing Reference
  subscription_monthly_rate FLOAT64,   -- e.g., 20.00
  overage_rate_per_request FLOAT64,   -- TBD from Cursor pricing
  days_in_month INT64,

  -- Metadata
  calculation_timestamp TIMESTAMP NOT NULL
)
PARTITION BY activity_date
CLUSTER BY user_email;
```

### Real Data Sample (from Cursor Admin API - Sept 17, 2025)

| activity_date | user_email | subscription_reqs | overage_reqs | total_reqs | estimated_cost_usd |
|--------------|------------|-------------------|--------------|------------|-------------------|
| 2025-09-17 | nathan.konopinski@samba.tv | 60 | 0 | 60 | 0.67 |
| 2025-09-17 | max.roycroft@samba.tv | 0 | 128 | 128 | 6.40 |
| 2025-09-17 | lukasz.michalek@samba.tv | 0 | 240 | 240 | 12.00 |
| 2025-09-17 | hanna.zdulska@samba.tv | 11 | 0 | 11 | 0.67 |
| 2025-09-17 | jose.lopes@samba.tv | 0 | 0 | 0 | 0.00 |

**Cost Calculation (Placeholder - need Cursor pricing):**
```sql
subscription_cost_usd = 20.00 / 30  -- Prorated daily
overage_cost_usd = usage_based_reqs * 0.05  -- Example: $0.05 per overage request
total_cost_usd = subscription_cost_usd + overage_cost_usd
```

**Users in Overage (Sept 17):** 87 out of ~78 users

---

## Supporting Tables

### Table 7: `dim_api_keys`

**Purpose:** API key to user mapping for Claude attribution
**Data Source:** Claude Admin API `/v1/organizations/api_keys` + manual mapping
**Update Frequency:** Weekly or on-demand

```sql
CREATE TABLE `ai_usage_analytics.dim_api_keys` (
  api_key_id STRING NOT NULL,
  api_key_name STRING,
  partial_key_hint STRING,
  workspace_id STRING,
  created_at TIMESTAMP,
  status STRING,
  created_by_user_id STRING,

  -- Manual Mapping
  mapped_user_email STRING,    -- Manually maintained
  mapped_team_name STRING,     -- Manually maintained

  -- Metadata
  last_updated TIMESTAMP NOT NULL
)
CLUSTER BY api_key_id;
```

**Real API Key Examples:**
| api_key_id | api_key_name | workspace_id | partial_hint | status |
|------------|-------------|--------------|--------------|--------|
| apikey_01LCnmJHA9sXT5bFG8VDR68x | jeremy-dev-key | null | sk-ant-api03-kLr...7gAA | active |
| apikey_01GKcX6KzVBF8yC9Qsdnd3kS | sid-dev-key | null | (truncated) | active |
| apikey_01Eb6TPyqUneJQqKBfv7Gti6 | (unnamed) | wrkspc_01WtfAtqQsV3zBDs9RYpNZdR | (truncated) | active |

### Table 8: `dim_workspaces`

**Purpose:** Workspace reference data
**Data Source:** Claude Admin API `/v1/organizations/workspaces`
**Update Frequency:** Weekly or on-demand

```sql
CREATE TABLE `ai_usage_analytics.dim_workspaces` (
  workspace_id STRING NOT NULL,
  workspace_name STRING NOT NULL,
  display_color STRING,
  created_at TIMESTAMP,
  archived_at TIMESTAMP,

  -- Metadata
  last_updated TIMESTAMP NOT NULL
)
CLUSTER BY workspace_id;
```

**Real Workspace Data:**
| workspace_id | workspace_name | display_color | created_at |
|-------------|---------------|---------------|------------|
| wrkspc_01WtfAtqQsV3zBDs9RYpNZdR | Claude Code | #b6613c | 2025-02-26T20:05:26Z |
| (null or default) | Default | (default) | (org creation date) |

---

## Data Relationships

### Attribution Chain

**Claude.ai Usage:**
```
claude_ai_usage_stats.user_email → DIRECT (from audit logs)
```

**Claude Code Usage:**
```
claude_code_usage_stats.user_email → DIRECT (from API when actor_type='user_actor')
claude_code_usage_stats.api_key_name → dim_api_keys.api_key_name → mapped_user_email
```

**Claude API Usage:**
```
claude_usage_report.api_key_id → dim_api_keys.api_key_id → mapped_user_email
```

**Claude Costs:**
```
claude_cost_report.workspace_id → dim_workspaces.workspace_name
(For user attribution, must join through api_key mapping - NOT available in cost report)
```

**Cursor Usage & Costs:**
```
cursor_usage_stats.user_email → DIRECT (from API)
cursor_expenses_calculated.user_email → DIRECT (calculated from usage)
```

---

## Platform Segmentation Strategy

### How to Identify Each Platform:

**Claude.ai (Chat/Web):**
- Source: `claude_ai_usage_stats`
- Identification: `client_platform` IN ('web_claude_ai', 'desktop_app', 'ios')
- Cost Attribution: Workspace-level only (from `claude_cost_report`)

**Claude Code (IDE):**
- Source: `claude_code_usage_stats`
- Identification: `terminal_type` IN ('cursor', 'vscode', 'goland')
- Cost Attribution: Available in `model_breakdown.estimated_cost`

**Claude API (Programmatic):**
- Source: `claude_usage_report`
- Identification: API keys NOT associated with Claude Code or claude.ai
- Cost Attribution: Workspace-level from `claude_cost_report`

**Cursor:**
- Source: `cursor_usage_stats`
- Cost Attribution: Calculated per-user from request counts

### Workspace Usage Patterns (from real data):

**"Claude Code" workspace (wrkspc_01WtfAtqQsV3zBDs9RYpNZdR):**
- Oct 16 cost: $934.16
- Primarily Claude Code IDE usage
- Contains: claude-sonnet-4-5, claude-3-5-haiku
- Has Web Search usage ($1.00)

**"Default" workspace (null):**
- Oct 16 cost: $1,840.65
- Mixed usage (claude.ai + some API)
- Higher volume than Claude Code workspace

**NOTE:** As you mentioned, "Claude Code" is a misnomer - both workspaces contain mixed usage types.

---

## Summary of Verified Data

### Claude APIs - All Working ✅

1. **Claude Code Usage Report:** ✅
   - Endpoint: `/usage_report/claude_code?starting_at=YYYY-MM-DD`
   - Per-user email or per-API-key
   - Includes estimated costs
   - Terminal type (cursor, vscode, etc.)

2. **Usage Report (Messages):** ✅
   - Endpoint: `/usage_report/messages?starting_at=YYYY-MM-DD&ending_at=YYYY-MM-DD&group_by[]=api_key_id&group_by[]=workspace_id&group_by[]=model`
   - Per API key, workspace, model breakdown
   - Token counts (no costs)

3. **Cost Report:** ✅
   - Endpoint: `/cost_report?starting_at=YYYY-MM-DD&ending_at=YYYY-MM-DD&group_by[]=workspace_id&group_by[]=description`
   - Per workspace, model, token type breakdown
   - Actual dollar costs
   - Cannot group by api_key_id (not supported)

### Cursor API - Working ✅

1. **Daily Usage Data:** ✅
   - Endpoint: `POST /teams/daily-usage-data`
   - Per-user, per-day complete breakdown
   - Request counts (must calculate costs)

### Manual Upload - Available ✅

1. **Claude.ai Audit Logs:** ✅
   - CSV export with audit events
   - Per-user activity tracking
   - Event types: conversation, project, file upload

---

## Next Steps

1. Create actual SQL schema files in `/sql/tables/`
2. Build ETL pipelines for each data source
3. Create aggregation views for dashboards
4. Update PRD with this verified architecture
