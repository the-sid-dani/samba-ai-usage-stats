# VERIFIED API DATA STRUCTURES

**Investigation Date:** October 17, 2025
**Source Files:** `scripts/api_investigation/responses/`

This document contains ACTUAL API response structures verified through live testing.

---

## 🚨 CRITICAL FINDINGS

### 1. **Claude Admin API - ALL Metadata Fields are NULL**
- ❌ **Cannot segment platforms** (claude.ai vs Claude Code vs API)
- ❌ All these fields return `null`:
  - `workspace_id`
  - `description`
  - `model`
  - `cost_type`
  - `token_type`
  - `api_key_id`

**Impact:** We CANNOT distinguish between claude.ai, Claude Code, and API costs from this endpoint.

### 2. **Cursor API - NO Dollar Amounts**
- ✅ Has request count fields
- ❌ **NO actual cost/price fields**
- Must **calculate costs ourselves** using Cursor pricing tiers

---

## Claude Admin API - Cost Report

**Endpoint:** `GET /v1/organizations/cost_report`
**Tested:** ✅ SUCCESS
**Records:** 3 days with data, 4 days empty

### Actual Response Structure

```json
{
  "data": [
    {
      "starting_at": "2025-09-17T00:00:00Z",
      "ending_at": "2025-09-18T00:00:00Z",
      "results": [
        {
          "currency": "USD",
          "amount": "83391.52823",
          "workspace_id": null,          // ❌ NULL
          "description": null,            // ❌ NULL
          "cost_type": null,              // ❌ NULL
          "context_window": null,         // ❌ NULL
          "model": null,                  // ❌ NULL
          "service_tier": null,           // ❌ NULL
          "token_type": null              // ❌ NULL
        }
      ]
    }
  ],
  "has_more": true,
  "next_page": "page_MjAyNS0wOS0yNFQwMDowMDowMFo="
}
```

### Available Fields
- ✅ `currency` - Always "USD"
- ✅ `amount` - Total daily cost (string, decimal)
- ✅ `starting_at` - Date bucket start (ISO 8601)
- ✅ `ending_at` - Date bucket end (ISO 8601)
- ✅ `has_more` - Pagination flag
- ✅ `next_page` - Pagination cursor

### Sample Data (3 days)
| Date | Amount (USD) |
|------|--------------|
| Sept 17 | $83,391.53 |
| Sept 18 | $151,452.04 |
| Sept 19 | $187,515.35 |

**Total 3-day spend:** $422,358.92

---

## Claude Admin API - Usage Report (Messages)

**Endpoint:** `GET /v1/organizations/usage_report/messages`
**Tested:** ✅ SUCCESS
**Records:** 3 days with data

### Actual Response Structure

```json
{
  "data": [
    {
      "starting_at": "2025-09-17T00:00:00Z",
      "ending_at": "2025-09-18T00:00:00Z",
      "results": [
        {
          "uncached_input_tokens": 56047359,
          "cache_creation": {
            "ephemeral_1h_input_tokens": 0,
            "ephemeral_5m_input_tokens": 2777906
          },
          "cache_read_input_tokens": 51056717,
          "output_tokens": 2724851,
          "server_tool_use": {
            "web_search_requests": 0
          },
          "api_key_id": null,           // ❌ NULL
          "workspace_id": null,          // ❌ NULL
          "model": null,                 // ❌ NULL
          "service_tier": null,          // ❌ NULL
          "context_window": null         // ❌ NULL
        }
      ]
    }
  ]
}
```

### Available Fields (Token Counts)
- ✅ `uncached_input_tokens` - Fresh input tokens
- ✅ `cache_creation.ephemeral_1h_input_tokens` - 1-hour cache writes
- ✅ `cache_creation.ephemeral_5m_input_tokens` - 5-minute cache writes
- ✅ `cache_read_input_tokens` - Cache reads
- ✅ `output_tokens` - Generated tokens
- ✅ `server_tool_use.web_search_requests` - Web search tool calls

### Sample Data (Sept 17)
```
Input (uncached):        56,047,359 tokens
Cache Creation (5m):      2,777,906 tokens
Cache Reads:             51,056,717 tokens
Output:                   2,724,851 tokens
Web Search Requests:              0 requests
```

---

## Cursor Admin API - Daily Usage Data

**Endpoint:** `POST /teams/daily-usage-data`
**Tested:** ✅ SUCCESS
**Records:** 2,356 user-day records (30 days, ~78 users)

### Actual Response Structure

```json
{
  "period": {
    "startDate": 1760120651123,
    "endDate": 1760725451123
  },
  "data": [
    {
      "date": 1758133588288,
      "day": "2025-09-17",
      "userId": "user_tkWgPDhUwGn2FzKlyV5iqodPBN",
      "email": "nathan.konopinski@samba.tv",
      "isActive": true,

      // Productivity Metrics
      "totalLinesAdded": 6823,
      "totalLinesDeleted": 373,
      "acceptedLinesAdded": 478,
      "acceptedLinesDeleted": 150,

      // AI Interaction Metrics
      "totalApplies": 28,
      "totalAccepts": 7,
      "totalRejects": 0,
      "totalTabsShown": 97,
      "totalTabsAccepted": 16,

      // Request Type Breakdown
      "composerRequests": 0,
      "chatRequests": 0,
      "agentRequests": 60,
      "cmdkUsages": 0,

      // Cost/Finance Fields (REQUEST COUNTS, NOT DOLLARS)
      "subscriptionIncludedReqs": 60,    // Within 500/month limit
      "apiKeyReqs": 0,                    // API key usage
      "usageBasedReqs": 0,                // Overage requests

      // Context
      "bugbotUsages": 0,
      "mostUsedModel": "claude-4-sonnet",
      "applyMostUsedExtension": "go",
      "tabMostUsedExtension": "Untitled-1",
      "clientVersion": "1.6.26"
    }
  ]
}
```

### All Available Fields

**Identifiers:**
- ✅ `date` - Unix timestamp (milliseconds)
- ✅ `day` - Date string (YYYY-MM-DD)
- ✅ `userId` - Cursor user ID
- ✅ `email` - User email (direct attribution)
- ✅ `isActive` - Boolean activity flag

**Productivity Metrics:**
- ✅ `totalLinesAdded` - Lines suggested by AI
- ✅ `totalLinesDeleted` - Lines deleted with AI
- ✅ `acceptedLinesAdded` - Lines accepted by developer
- ✅ `acceptedLinesDeleted` - Accepted deletions

**AI Interactions:**
- ✅ `totalApplies` - AI suggestions applied
- ✅ `totalAccepts` - AI suggestions accepted
- ✅ `totalRejects` - AI suggestions rejected
- ✅ `totalTabsShown` - Tab completions shown
- ✅ `totalTabsAccepted` - Tab completions accepted

**Request Types:**
- ✅ `composerRequests` - Long-form code generation
- ✅ `chatRequests` - Q&A interactions
- ✅ `agentRequests` - Autonomous code changes
- ✅ `cmdkUsages` - Inline Cmd+K edits
- ✅ `bugbotUsages` - Bug detection usage

**Finance/Cost Fields (REQUEST COUNTS):**
- ✅ `subscriptionIncludedReqs` - Requests within subscription (≤500/month)
- ✅ `usageBasedReqs` - Overage requests (pay-per-use)
- ✅ `apiKeyReqs` - Direct API key usage

**Context:**
- ✅ `mostUsedModel` - Primary AI model (e.g., "claude-4-sonnet", "gpt-5")
- ✅ `applyMostUsedExtension` - Most common file type for applies
- ✅ `tabMostUsedExtension` - Most common file type for tabs
- ✅ `clientVersion` - Cursor IDE version

### Sample High-Usage Records

**User: nathan.konopinski@samba.tv (Sept 17)**
```
Lines Added: 6,823 (478 accepted = 7% acceptance rate)
Agent Requests: 60
Subscription Reqs: 60 (within limit)
Model: claude-4-sonnet
```

**User: max.roycroft@samba.tv (Sept 17)**
```
Lines Added: 182 (144 accepted = 79% acceptance rate)
Composer Requests: 104
Agent Requests: 24
Usage-Based Reqs: 128 (OVERAGE - beyond 500 limit)
Model: claude-4-sonnet-1m-thinking
```

**User: lukasz.michalek@samba.tv (Sept 17)**
```
Composer Requests: 169
Agent Requests: 71
Usage-Based Reqs: 240 (HEAVY OVERAGE)
Model: claude-4-sonnet
```

### Field Value Ranges (Across 2,356 records)

| Field | Max Value | Records with Data |
|-------|-----------|-------------------|
| `subscriptionIncludedReqs` | 432 | 388 records |
| `usageBasedReqs` | 584 | 87 records |
| `apiKeyReqs` | 12 | 9 records |
| `composerRequests` | 512 | 119 records |
| `chatRequests` | 26 | 77 records |
| `totalLinesAdded` | 27,629 | 326 records |

---

## 🚨 MAJOR DATA GAPS

### Cannot Get from APIs:

1. **Claude.ai Usage Data**
   - ❌ No API endpoint available
   - ⚠️  Must use manual CSV/audit log upload workflow

2. **Claude Code Usage Data**
   - ❌ `/claude_code` endpoint parameters unclear (different from cost_report)
   - ⚠️  Need to investigate correct parameter format

3. **Platform Segmentation**
   - ❌ Cannot distinguish claude.ai vs Claude Code vs API from cost data
   - ❌ All metadata fields return null
   - ⚠️  May need to use workspace IDs or other approach

4. **Cursor Dollar Costs**
   - ❌ API only provides request counts, not actual costs
   - ⚠️  Must calculate using pricing model:
     - Subscription: $20/user/month base (500 requests included)
     - Overage: Price per request beyond 500
     - API Key: Separate pricing

---

## NEXT STEPS

### Immediate Actions Needed:

1. **Fix Claude Code endpoint** - Investigate correct parameters for `/claude_code`
2. **Investigate workspace_id approach** - Check if we can use workspace IDs to segment platforms
3. **Define Cursor cost calculation** - Get Cursor pricing model for overage requests
4. **Design manual upload workflow** - For claude.ai usage data (no API available)

### Data Architecture Impact:

**Current PRD is WRONG** because it assumes:
- ✅ We can segment Claude platforms from Cost Report → **FALSE** (all fields null)
- ✅ Cursor API provides dollar costs → **FALSE** (only request counts)
- ✅ We can use workspace_id for attribution → **UNKNOWN** (need to test)

**Must revise PRD** to reflect:
- Manual claude.ai upload workflow
- Cost calculation logic for Cursor
- Alternative platform segmentation approach
- Proper field mappings from verified data

---

**Files:** All raw JSON responses saved in `scripts/api_investigation/responses/`
