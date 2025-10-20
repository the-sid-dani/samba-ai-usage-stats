# Data Architecture

## BigQuery Tables (6 Tables)

### 1. `claude_usage_stats`
**Purpose:** Claude.ai chat/web interface usage
**Data Source:** Manual upload to Google Sheets → BigQuery sync
**Key Fields:**
- `user_email` - User attribution
- `activity_date` - Date of usage
- `conversation_count` - Number of conversations
- `message_count` - Number of messages sent
- `project_count` - Number of projects created
- `file_upload_count` - Files uploaded to conversations
- `upload_timestamp` - When data was uploaded (for freshness tracking)

**Update Frequency:** Manual (weekly or monthly)

### 2. `claude_code_usage_stats`
**Purpose:** Claude Code IDE productivity metrics
**Data Source:** Claude Admin API `/claude_code` endpoint
**Key Fields:**
- `user_email` - Direct email attribution
- `activity_date` - Date of usage
- `num_sessions` - IDE sessions
- `commits_by_claude_code` - Git commits with AI
- `pull_requests_by_claude_code` - PRs created with AI
- `lines_added` - Lines added with AI assistance
- `lines_removed` - Lines removed with AI assistance
- `edit_tool_accepted` - File edits accepted
- `edit_tool_rejected` - File edits rejected
- `model` - AI model used
- `estimated_cost_usd` - Usage-based cost
- `input_tokens`, `output_tokens`, `cache_tokens` - Token usage

**Update Frequency:** Daily automated

### 3. `cursor_usage_stats`
**Purpose:** Cursor IDE productivity and interaction metrics
**Data Source:** Cursor Admin API `/teams/daily-usage-data`
**Key Fields:**
- `user_email` - Direct email attribution
- `activity_date` - Date of usage
- `is_active` - User activity flag
- `total_lines_added` - Lines suggested by AI
- `accepted_lines_added` - Lines accepted by developer
- `total_applies` - AI suggestions applied
- `total_accepts` - AI suggestions accepted
- `total_rejects` - AI suggestions rejected
- `composer_requests` - Long-form code generation
- `chat_requests` - Q&A interactions
- `agent_requests` - Autonomous code changes
- `cmdk_usages` - Inline edit requests
- `subscription_included_reqs` - Within subscription (≤500)
- `usage_based_reqs` - Overage requests
- `most_used_model` - Primary AI model
- `client_version` - Cursor version

**Update Frequency:** Daily automated

### 4. `claude_expenses`
**Purpose:** All Claude platform costs (claude.ai + Claude Code + API combined)
**Data Source:** Claude Admin API Cost Report
**Key Fields:**
- `expense_date` - Date of cost
- `platform` - "claude.ai" | "claude_code" | "claude_api"
- `workspace_id` - Workspace attribution
- `model` - AI model driving cost
- `cost_usd` - Cost in USD
- `cost_type` - "tokens" | "subscription" | "other"
- `token_type` - "input" | "output" | "cache_read" (if applicable)
- `service_tier` - Service level

**Update Frequency:** Daily automated

**Platform Segmentation Logic:**
- Use `workspace_id` or API endpoint patterns to distinguish claude.ai vs Claude Code vs API usage
- Aggregate by platform for dashboard filtering

### 5. `cursor_expenses`
**Purpose:** Cursor subscription and overage costs
**Data Source:** Cursor Admin API `/teams/daily-usage-data` (cost fields)
**Key Fields:**
- `expense_date` - Date of cost
- `user_email` - User attribution
- `cost_type` - "subscription" | "usage_based" | "api_key"
- `subscription_included_reqs` - Requests within plan
- `usage_based_reqs` - Overage requests
- `estimated_cost_usd` - Total cost
- `subscription_plan` - Plan type

**Update Frequency:** Daily automated

**Cost Calculation:**
```
total_cost = (subscription_base / days_in_month) + (usage_based_reqs × overage_rate)
```

### 6. `api_usage_expenses`
**Purpose:** Claude API programmatic usage costs ONLY (not Cursor API)
**Data Source:** Claude Admin API Cost Report (filtered)
**Key Fields:**
- `expense_date` - Date of cost
- `api_key_id` - API key attribution
- `model` - AI model used
- `cost_usd` - Cost in USD
- `input_tokens` - Input token count
- `output_tokens` - Output token count
- `cache_tokens` - Cache token usage
- `endpoint` - API endpoint used (messages, batch, etc.)
- `service_tier` - Service level

**Update Frequency:** Daily automated

**Filtering Logic:**
- Include ONLY programmatic API usage (Messages API, Batch API, Tools API)
- Exclude Claude Code and claude.ai costs (those go in `claude_expenses`)
- Use API key patterns or workspace IDs to filter

## Data Flow Architecture

```
┌─────────────────────┐
│  Data Sources       │
├─────────────────────┤
│ 1. Google Sheets    │──► Manual Upload ──────► claude_usage_stats
│ 2. Claude Admin API │──► /claude_code ────────► claude_code_usage_stats
│    (3 endpoints)    │──► Cost Report ─────────► claude_expenses
│                     │──► Cost Report (filter)─► api_usage_expenses
│ 3. Cursor Admin API │──► /daily-usage-data ───► cursor_usage_stats
│                     │──► /daily-usage-data ───► cursor_expenses
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  BigQuery Tables    │
│  (6 tables)         │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Metabase           │
│  (4 dashboards)     │
└─────────────────────┘
```

## API Key Mapping Strategy

**Challenge:** Claude API Cost Report returns `api_key_id`, not email
**Solution:** Maintain mapping table in Google Sheets:
- `api_key_id` → `user_email`
- `api_key_id` → `team_name`
- Manual maintenance by admin

**Table:** `dim_api_key_mapping` (BigQuery)
- Synced from Google Sheets
- Used for JOIN with `api_usage_expenses` and `claude_expenses`

---
