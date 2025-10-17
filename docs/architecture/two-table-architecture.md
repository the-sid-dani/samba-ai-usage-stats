# 🗄️ **TWO-TABLE ARCHITECTURE**

## **fact_cursor_daily_usage** (AI Coding Agent - Cursor)

**Purpose:** Cursor-specific coding productivity metrics with direct email attribution and hybrid cost model.

**Key Attributes:**
- user_email: STRING - Direct attribution from Cursor API (high confidence)
- usage_date: DATE - Date of coding activity
- total_lines_added: INT64 - Lines suggested by Cursor AI
- accepted_lines_added: INT64 - Lines accepted by developer
- total_accepts: INT64 - Number of suggestion acceptances
- total_rejects: INT64 - Number of suggestion rejections
- total_tabs_shown: INT64 - Tab completion suggestions shown
- total_tabs_accepted: INT64 - Tab completions accepted
- composer_requests: INT64 - Long-form code generation requests
- chat_requests: INT64 - Q&A interactions with AI
- agent_requests: INT64 - Autonomous code change requests
- cmdk_usages: INT64 - Cmd+K inline requests
- subscription_included_reqs: INT64 - Requests within subscription limit (≤500)
- usage_based_reqs: INT64 - Overage requests beyond subscription
- api_key_reqs: INT64 - Direct API usage
- most_used_model: STRING - Primary AI model used
- client_version: STRING - Cursor client version
- estimated_subscription_cost: FLOAT64 - Allocated monthly subscription cost
- estimated_overage_cost: FLOAT64 - Usage-based overage costs

### TypeScript Interface
```typescript
interface CursorDailyUsage {
  user_email: string;
  usage_date: string; // YYYY-MM-DD
  total_lines_added: number;
  accepted_lines_added: number;
  total_accepts: number;
  total_rejects: number;
  subscription_included_reqs: number;
  usage_based_reqs: number;
  most_used_model: string;
  line_acceptance_rate: number; // calculated
  estimated_total_cost: number; // calculated
}
```

## **fact_claude_daily_usage** (All Claude Platforms)

**Purpose:** Unified Claude ecosystem metrics supporting three distinct platforms with platform-specific attribution and metrics.

**Key Attributes:**
- platform: STRING - 'claude_code', 'claude_api', 'claude_ai'
- user_email: STRING - User attribution (Claude Code, claude.ai)
- api_key_id: STRING - API key attribution (Claude API, some Claude Code)
- workspace_id: STRING - Platform detection and grouping
- usage_date: DATE - Date of AI usage

**Claude Code Specific (Engineering Productivity):**
- claude_code_sessions: INT64 - IDE sessions with AI assistance
- claude_code_lines_added: INT64 - Lines added with AI help
- claude_code_lines_removed: INT64 - Lines removed with AI help
- claude_code_commits: INT64 - Git commits created with AI
- claude_code_prs: INT64 - Pull requests created with AI
- edit_tool_accepted/rejected: INT64 - File editing tool metrics
- multi_edit_tool_accepted/rejected: INT64 - Multi-file editing metrics
- write_tool_accepted/rejected: INT64 - New file creation metrics
- notebook_edit_tool_accepted/rejected: INT64 - Jupyter notebook editing

**Claude API Specific (Token Consumption):**
- uncached_input_tokens: INT64 - Fresh input tokens
- cached_input_tokens: INT64 - Cache hit tokens
- cache_read_input_tokens: INT64 - Cache read tokens
- output_tokens: INT64 - Generated output tokens
- web_search_requests: INT64 - Server tool usage

**Claude.ai Specific (Knowledge Work):**
- claude_ai_conversations: INT64 - Web conversations created
- claude_ai_projects: INT64 - Projects created/managed
- claude_ai_files_uploaded: INT64 - Files analyzed
- claude_ai_messages_sent: INT64 - Chat messages in conversations

**Universal Fields:**
- model: STRING - AI model used (claude-3-5-sonnet, etc.)
- total_cost_usd: FLOAT64 - Daily cost for this platform
- attribution_confidence: FLOAT64 - User attribution confidence (0.0-1.0)

### TypeScript Interface
```typescript
interface ClaudeDailyUsage {
  platform: 'claude_code' | 'claude_api' | 'claude_ai';
  user_email: string;
  api_key_id?: string;
  usage_date: string; // YYYY-MM-DD

  // Claude Code specific
  claude_code_lines_added?: number;
  claude_code_acceptance_rate?: number;

  // Claude API specific
  uncached_input_tokens?: number;
  output_tokens?: number;

  // claude.ai specific
  claude_ai_conversations?: number;
  claude_ai_projects?: number;

  // Universal
  model: string;
  total_cost_usd: number;
  attribution_confidence: number;
}
```

## **Enhanced Dimension Tables**

### **dim_users_enhanced**
**Purpose:** Comprehensive user dimension with organizational hierarchy for advanced drill-down analytics.

**Key Attributes:**
- user_sk: INT64 - Surrogate key
- user_email: STRING - Primary identifier
- full_name: STRING - Complete name for display
- department: STRING - Engineering, Product, Marketing, etc.
- sub_department: STRING - Backend, Frontend, Data, QA, etc.
- team: STRING - Specific team assignment
- job_level: STRING - Junior, Mid, Senior, Staff, Principal
- manager_email: STRING - Manager for hierarchy analysis
- ai_user_type: STRING - 'engineering', 'knowledge_worker', 'hybrid'
- ai_budget_monthly_usd: FLOAT64 - Allocated AI budget
- is_active: BOOLEAN - Current employment status

### **dim_date**
**Purpose:** Time dimension table optimized for Metabase filtering and fiscal reporting.

**Key Attributes:**
- date_sk: INT64 - Date key (YYYYMMDD format)
- calendar_date: DATE - Actual date
- year_month_label: STRING - "2025-09" for Metabase
- quarter_label: STRING - "Q3 2025" for Metabase
- fiscal_year: INT64 - Fiscal year for business reporting
- is_business_day: BOOLEAN - Weekday flag for productivity analysis

### Relationships
- fact_cursor_daily_usage ↔ dim_users_enhanced (via user_email)
- fact_claude_daily_usage ↔ dim_users_enhanced (via user_email)
- fact_cursor_daily_usage ↔ dim_date (via usage_date)
- fact_claude_daily_usage ↔ dim_date (via usage_date)
- api_key_mappings ↔ fact_claude_daily_usage (via api_key_id)

---
