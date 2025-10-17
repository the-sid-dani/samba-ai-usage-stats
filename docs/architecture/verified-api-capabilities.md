# 🔌 **VERIFIED API CAPABILITIES**

Based on comprehensive API testing and documentation review, here are the **confirmed data sources** with exact field mappings:

## **Claude Admin API Integration (Multi-Endpoint)**

### **Claude Code Analytics API** ✅ **VERIFIED**
**Endpoint:** `https://api.anthropic.com/v1/organizations/usage_report/claude_code`
**Purpose:** Rich engineering productivity metrics for Claude Code IDE integration
**Authentication:** Admin API key with x-api-key header
**Attribution:** Direct email attribution (high confidence)

**Response Schema:**
```typescript
interface ClaudeCodeAnalyticsResponse {
  data: Array<{
    actor: {
      email_address: string;        // ✅ Direct user attribution
      type: "user_actor" | "api_actor";
    };
    core_metrics: {
      commits_by_claude_code: number;     // ✅ Git productivity
      lines_of_code: {
        added: number;                    // ✅ Lines added with AI
        removed: number;                  // ✅ Lines removed with AI
      };
      num_sessions: number;               // ✅ IDE sessions
      pull_requests_by_claude_code: number; // ✅ PR productivity
    };
    tool_actions: {
      edit_tool: {
        accepted: number;                 // ✅ File editing acceptance
        rejected: number;                 // ✅ File editing rejection
      };
      multi_edit_tool: { accepted: number; rejected: number; };
      write_tool: { accepted: number; rejected: number; };
      notebook_edit_tool: { accepted: number; rejected: number; };
    };
    model_breakdown: Array<{
      model: string;                      // ✅ Claude model used
      estimated_cost: { amount: number; currency: "USD"; };
      tokens: {
        input: number;
        output: number;
        cache_creation: number;
        cache_read: number;
      };
    }>;
  }>;
  has_more: boolean;
  next_page: string | null;
}
```

### **Claude Usage Report API** ✅ **VERIFIED**
**Endpoint:** `https://api.anthropic.com/v1/organizations/usage_report/messages`
**Purpose:** Token consumption across Claude API and mixed Claude Code usage
**Authentication:** Admin API key with x-api-key header
**Attribution:** API key attribution (requires mapping)

**Response Schema:**
```typescript
interface ClaudeUsageReportResponse {
  data: Array<{
    starting_at: string;              // ✅ Date bucket
    ending_at: string;
    results: Array<{
      api_key_id: string;             // ✅ User attribution via mapping
      workspace_id: string;          // ✅ Platform detection
      model: string;                  // ✅ Claude model
      uncached_input_tokens: number; // ✅ Fresh input tokens
      cached_input_tokens: number;   // ✅ Cache hits
      cache_read_input_tokens: number; // ✅ Cache reads
      output_tokens: number;         // ✅ Generated tokens
      cache_creation: {
        ephemeral_1h_input_tokens: number;
        ephemeral_5m_input_tokens: number;
      };
      server_tool_use: {
        web_search_requests: number;  // ✅ Tool usage
      };
      service_tier: string;           // ✅ Priority level
      context_window: string;         // ✅ Model context
    }>;
  }>;
  has_more: boolean;
  next_page: string | null;
}
```

### **Claude Cost Report API** ✅ **VERIFIED**
**Endpoint:** `https://api.anthropic.com/v1/organizations/cost_report`
**Purpose:** Detailed cost breakdown with workspace and token-type granularity
**Authentication:** Admin API key with x-api-key header
**Attribution:** Workspace-level (requires allocation)

**Response Schema:**
```typescript
interface ClaudeCostReportResponse {
  data: Array<{
    starting_at: string;
    ending_at: string;
    results: Array<{
      currency: "USD";
      amount: string;                 // ✅ Cost in USD (decimal string)
      workspace_id: string;          // ✅ Workspace attribution
      description: string;           // ✅ Cost description
      cost_type: "tokens";          // ✅ Cost category
      model: string;                 // ✅ Model driving cost
      service_tier: string;         // ✅ Service level
      token_type: "uncached_input_tokens" | "output_tokens" | "cache_read_input_tokens";
      context_window: string;
    }>;
  }>;
}
```

### **Cursor Admin API Integration** ✅ **VERIFIED**

**Endpoint:** `https://api.cursor.com/teams/daily-usage-data`
**Purpose:** Comprehensive coding productivity metrics with direct email attribution and hybrid cost model
**Authentication:** Bearer token in Authorization header
**Rate Limits:** 90-day maximum date range per request
**Attribution:** Direct email attribution (highest confidence)

**Response Schema:**
```typescript
interface CursorUsageResponse {
  data: Array<{
    email: string;                    // ✅ Direct user attribution (no mapping needed)
    date: string | number;            // ✅ Date (string or Unix timestamp)
    isActive: boolean;                // ✅ User activity flag

    // ✅ VERIFIED Productivity Metrics
    totalLinesAdded: number;          // Lines suggested by AI
    totalLinesDeleted: number;        // Lines deleted with AI help
    acceptedLinesAdded: number;       // Lines accepted by developer
    acceptedLinesDeleted: number;     // Accepted deletions

    // ✅ VERIFIED AI Interaction Metrics
    totalApplies: number;             // AI suggestions applied
    totalAccepts: number;             // AI suggestions accepted
    totalRejects: number;             // AI suggestions rejected
    totalTabsShown: number;           // Tab completion suggestions
    totalTabsAccepted: number;        // Tab completions accepted

    // ✅ VERIFIED Request Type Breakdown
    composerRequests: number;         // Long-form code generation
    chatRequests: number;             // Q&A with AI
    agentRequests: number;            // Autonomous code changes
    cmdkUsages: number;               // Cmd+K inline requests

    // ✅ VERIFIED Cost Attribution
    subscriptionIncludedReqs: number; // Within subscription limit (≤500)
    usageBasedReqs: number;           // Beyond subscription (overage)
    apiKeyReqs: number;               // Direct API usage

    // ✅ VERIFIED Context Data
    mostUsedModel: string;            // Primary AI model
    clientVersion: string;            // Cursor version
    applyMostUsedExtension: string;   // Programming language context
    tabMostUsedExtension: string;     // Tab completion context
  }>;
  period: {
    start: string;
    end: string;
  };
}
```

### **claude.ai Enterprise Audit Logs** ✅ **VERIFIED - MANUAL EXPORT ONLY**
**Source:** Enterprise audit log CSV/JSON export via Enterprise Console
**Purpose:** Knowledge worker productivity via conversation and project metrics
**Authentication:** Manual export from claude.ai Enterprise Console → Settings → Data management → Export logs
**Attribution:** Direct email attribution from audit events
**Access Level:** Enterprise subscription required
**Data Retention:** 180 days, 24-hour download link expiry

⚠️ **IMPORTANT**: No programmatic API endpoint available. Manual export workflow required.

**Manual Export Process:**
1. Login to claude.ai Enterprise Console
2. Navigate to Settings → Data management
3. Click "Export logs" button
4. Download CSV/JSON file (24-hour link expiry)
5. Process file locally via `claude_ai_client.py`

**Data Schema:**
```typescript
interface ClaudeAiAuditEvent {
  actor: {
    name: string;
    email: string;                    // ✅ Direct user attribution
  };
  event_type: "conversation_created" | "project_created" | "file_uploaded";
  timestamp: string;                  // ✅ Event timestamp
  metadata: {
    conversation_id?: string;
    project_id?: string;
    file_name?: string;
    file_size?: number;
  };
}
```

**Future Consideration:** Anthropic Compliance API (August 2025) may provide programmatic access but requires enterprise provisioning and documentation not yet public.

### Metabase Management API

**Purpose:** Programmatic dashboard management and configuration

**Base URL:** `https://metabase-vm.internal/api`
**Authentication:** Session token or API key
**Rate Limits:** Standard web application limits

**Key Endpoints Used:**
- `POST /api/session` - Authentication and session management
- `GET /api/dashboard` - List available dashboards
- `POST /api/dashboard` - Create new dashboard
- `PUT /api/dashboard/{id}` - Update dashboard configuration
- `GET /api/card` - List dashboard cards/widgets
- `POST /api/card` - Create new dashboard widget

**Request/Response Schema:**
```typescript
// Dashboard Creation Request
interface CreateDashboardRequest {
  name: string;
  description?: string;
  collection_id?: number;
  parameters?: Array<{
    name: string;
    type: string;
    default?: any;
  }>;
}

// Dashboard Response
interface DashboardResponse {
  id: number;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  collection_id: number;
  parameters: Array<{
    id: string;
    name: string;
    type: string;
    default: any;
  }>;
}
```

---
