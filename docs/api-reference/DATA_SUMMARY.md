# Complete API Data Summary

**Date:** October 17, 2025
**Status:** VERIFIED via live API testing

---

## What Data We Can Actually Get

### 1. Claude Admin API - Cost Report ✅

**Endpoint:** `GET /v1/organizations/cost_report?starting_at=YYYY-MM-DD&ending_at=YYYY-MM-DD`

**What We GET:**
```
✅ currency: "USD"
✅ amount: "83391.52823" (daily total cost)
✅ starting_at: "2025-09-17T00:00:00Z"
✅ ending_at: "2025-09-18T00:00:00Z"
✅ has_more: true/false
✅ next_page: "pagination_cursor"
```

**What We DON'T GET:**
```
❌ workspace_id: null
❌ description: null
❌ model: null
❌ cost_type: null
❌ token_type: null
❌ service_tier: null
❌ api_key_id: null
❌ context_window: null
```

**What This Means:**
- ✅ We know: Total daily Claude spending ($83K, $151K, $187K per day)
- ❌ We DON'T know: Which platform (claude.ai vs Claude Code vs API)
- ❌ We DON'T know: Which user
- ❌ We DON'T know: Which model
- ❌ We DON'T know: What type of usage

**Table We Can Create:**
```
claude_total_daily_cost:
  - date (DATE)
  - amount_usd (DECIMAL)
  - organization_id (STRING)
```

That's it. Just 3 fields. No segmentation possible.

---

### 2. Claude Admin API - Usage Report (Messages) ✅

**Endpoint:** `GET /v1/organizations/usage_report/messages?starting_at=YYYY-MM-DD&ending_at=YYYY-MM-DD`

**What We GET:**
```
✅ uncached_input_tokens: 56047359
✅ cache_creation.ephemeral_1h_input_tokens: 0
✅ cache_creation.ephemeral_5m_input_tokens: 2777906
✅ cache_read_input_tokens: 51056717
✅ output_tokens: 2724851
✅ server_tool_use.web_search_requests: 0
```

**What We DON'T GET:**
```
❌ api_key_id: null
❌ workspace_id: null
❌ model: null
❌ service_tier: null
❌ context_window: null
```

**What This Means:**
- ✅ We know: Total daily token usage across org
- ❌ We DON'T know: Which user
- ❌ We DON'T know: Which platform
- ❌ We DON'T know: Which model

**Table We Can Create:**
```
claude_total_daily_tokens:
  - date (DATE)
  - uncached_input_tokens (INT64)
  - cache_5m_tokens (INT64)
  - cache_1h_tokens (INT64)
  - cache_read_tokens (INT64)
  - output_tokens (INT64)
  - web_search_requests (INT64)
```

Organization-level aggregates only. No user attribution.

---

### 3. Cursor Admin API - Daily Usage Data ✅

**Endpoint:** `POST /teams/daily-usage-data` with `{startDate: timestamp_ms, endDate: timestamp_ms}`

**What We GET (PER USER, PER DAY):**

**Identifiers:**
```
✅ date: 1758133588288 (Unix ms)
✅ day: "2025-09-17"
✅ userId: "user_tkWgPDhUwGn2FzKlyV5iqodPBN"
✅ email: "nathan.konopinski@samba.tv"  // DIRECT USER ATTRIBUTION!
✅ isActive: true
```

**Productivity:**
```
✅ totalLinesAdded: 6823
✅ totalLinesDeleted: 373
✅ acceptedLinesAdded: 478
✅ acceptedLinesDeleted: 150
```

**AI Interactions:**
```
✅ totalApplies: 28
✅ totalAccepts: 7
✅ totalRejects: 0
✅ totalTabsShown: 97
✅ totalTabsAccepted: 16
```

**Request Types:**
```
✅ composerRequests: 0
✅ chatRequests: 0
✅ agentRequests: 60
✅ cmdkUsages: 0
✅ bugbotUsages: 0
```

**Finance (REQUEST COUNTS - NOT DOLLARS):**
```
✅ subscriptionIncludedReqs: 60  // Requests within 500/month limit
✅ usageBasedReqs: 0              // Overage requests (charged extra)
✅ apiKeyReqs: 0                  // Direct API key usage
```

**Context:**
```
✅ mostUsedModel: "claude-4-sonnet"
✅ applyMostUsedExtension: "go"
✅ tabMostUsedExtension: "Untitled-1"
✅ clientVersion: "1.6.26"
```

**What We DON'T GET:**
```
❌ Actual dollar costs (no price/cost/billing fields)
```

**Table We Can Create:**
```
cursor_daily_user_usage:
  - date (DATE)
  - user_email (STRING)           // ✅ DIRECT ATTRIBUTION
  - user_id (STRING)
  - is_active (BOOL)

  // Productivity (all 4 fields)
  - total_lines_added (INT64)
  - total_lines_deleted (INT64)
  - accepted_lines_added (INT64)
  - accepted_lines_deleted (INT64)

  // AI Interactions (all 5 fields)
  - total_applies (INT64)
  - total_accepts (INT64)
  - total_rejects (INT64)
  - total_tabs_shown (INT64)
  - total_tabs_accepted (INT64)

  // Request Types (all 5 fields)
  - composer_requests (INT64)
  - chat_requests (INT64)
  - agent_requests (INT64)
  - cmdk_usages (INT64)
  - bugbot_usages (INT64)

  // Finance - Request Counts (all 3 fields)
  - subscription_included_reqs (INT64)
  - usage_based_reqs (INT64)
  - api_key_reqs (INT64)

  // Context (all 4 fields)
  - most_used_model (STRING)
  - apply_most_used_extension (STRING)
  - tab_most_used_extension (STRING)
  - client_version (STRING)

  // Calculated field
  - estimated_cost_usd (FLOAT64)  // We calculate this
```

**Sample Real Data (Sept 17):**

| User | Lines Added | Accepted | Composer | Agent | Overage Reqs | Model |
|------|-------------|----------|----------|-------|--------------|-------|
| nathan.konopinski | 6,823 | 478 (7%) | 0 | 60 | 0 | claude-4-sonnet |
| max.roycroft | 182 | 144 (79%) | 104 | 24 | **128** | claude-4-sonnet-1m |
| lukasz.michalek | 0 | 0 | 169 | 71 | **240** | claude-4-sonnet |
| hanna.zdulska | 317 | 206 (65%) | 0 | 11 | 0 | gpt-5 |

**87 users with overage requests** - This is where extra costs happen!

---

## Summary: What Tables We Can ACTUALLY Build

### Table 1: `claude_daily_cost` (Organization-level only)
```
Columns: 3
- date
- amount_usd
- organization_id

Attribution: NONE (organization aggregate)
Segmentation: NONE (all Claude platforms combined)
Source: Cost Report API
```

### Table 2: `claude_daily_tokens` (Organization-level only)
```
Columns: 7
- date
- uncached_input_tokens
- cache_5m_tokens
- cache_1h_tokens
- cache_read_tokens
- output_tokens
- web_search_requests

Attribution: NONE (organization aggregate)
Segmentation: NONE (all Claude platforms combined)
Source: Usage Report API
```

### Table 3: `cursor_daily_user_usage` (User-level! ✅)
```
Columns: 26 (see full list above)

Attribution: ✅ YES - Direct email attribution!
Segmentation: ✅ YES - Per user, per day
Source: Cursor API
Cost Calculation: ✅ Possible using request counts + pricing
```

---

## 🔥 THE BRUTAL TRUTH

### What We CAN Do:
1. ✅ Track **total Claude spending** per day (no breakdown)
2. ✅ Track **Cursor user-level productivity** (excellent detail)
3. ✅ Calculate **Cursor costs per user** (using request counts + pricing)
4. ✅ Build **Cursor productivity dashboards** (acceptance rates, etc.)

### What We CANNOT Do:
1. ❌ Segment Claude costs by platform (claude.ai vs Code vs API)
2. ❌ Attribute Claude costs to users (no user data in API)
3. ❌ Show which Claude models are used
4. ❌ Track Claude Code productivity metrics (no user-level data)

### The Gap:
- **Cursor:** Rich user-level data, excellent for analytics
- **Claude:** Only organization totals, very limited analytics

---

## Recommended Next Steps

### Option A: Accept Limitations
Build with what we have:
- Simple Claude cost tracking (org totals only)
- Rich Cursor analytics (user-level everything)
- Manual upload for claude.ai usage (if needed)

### Option B: Investigate Further
- Test `/claude_code` endpoint with different parameters
- Check if filtering by workspace_id returns better data
- Contact Anthropic support for attribution options

### Option C: Hybrid Approach
- Use what APIs provide (org totals for Claude)
- Add manual upload for user attribution
- Focus dashboard on Cursor (where we have good data)

**Which direction should we go?**
