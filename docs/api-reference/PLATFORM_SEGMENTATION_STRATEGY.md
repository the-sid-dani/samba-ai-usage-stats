# Platform Segmentation Strategy

**Organization ID:** `1233d3ee-9900-424a-a31a-fb8b8dcd0be3`

## Workspace Configuration

From Claude Console screenshot:

| Workspace | Created | API Keys | Notes |
|-----------|---------|----------|-------|
| **Default** | - | 41 keys | Main workspace |
| **Claude Code** | Feb 26, 2025 | 10 keys | **MISNOMER** - treat same as Default |

## 🚨 CRITICAL UNDERSTANDING

**User's Direction:** "Treat all keys the same from both workspaces"

**This means:**
- ❌ **We CANNOT segment by workspace** (both are mixed usage)
- ❌ **Workspace name "Claude Code" is misleading** (not just Claude Code usage)
- ✅ **All 51 API keys are for general Claude usage** (mix of claude.ai, Claude Code, API)

## Impact on Data Architecture

### Original Assumption (WRONG):
- Segment using workspace_id: Default = claude.ai, Claude Code workspace = Claude Code usage
- **This is FALSE**

### Reality:
- **We have NO WAY to distinguish** claude.ai vs Claude Code vs API usage from Cost Report
- All metadata fields are null (workspace_id, model, description, cost_type)
- Both workspaces contain mixed usage types

## Revised Approach

### Option 1: Single Combined Table (RECOMMENDED)
**Stop trying to segment platforms - treat as unified "Claude Ecosystem"**

**Table:** `claude_total_expenses`
- Contains ALL Claude costs (claude.ai + Claude Code + API combined)
- No platform field (can't reliably determine)
- Focus on total cost visibility and user attribution

**Benefits:**
- Accurate (reflects what API actually provides)
- Simple (no wrong assumptions)
- Complete (captures all Claude spending)

**Drawbacks:**
- Can't analyze claude.ai vs Claude Code separately
- Can't optimize per-platform

### Option 2: Use Usage Report to Infer Platform
**Try to infer platform from usage patterns in Messages API**

**Hypothesis:**
- High token usage + low request count = claude.ai (long conversations)
- Moderate tokens + high request count = Claude Code (frequent edits)
- Specific API key patterns = programmatic API

**Problems:**
- Speculative (not reliable)
- Complex logic with error potential
- Usage Report also has null metadata

### Option 3: Manual Workspace Mapping
**Create manual mapping table:**
- api_key_id → platform (claude.ai | Claude Code | API)
- Maintained by admin based on key usage knowledge

**Problems:**
- Manual maintenance burden
- Subject to human error
- Becomes stale quickly

## RECOMMENDED STRATEGY

### Simplified Data Model:

**For COSTS:**
1. **`claude_total_expenses`** - All Claude costs combined
   - Source: Cost Report API
   - No platform segmentation
   - Focus on total spend visibility

2. **`cursor_expenses`** - Cursor costs (calculated)
   - Source: Cursor API request counts + pricing model
   - Clear segmentation (it's all Cursor)

**For USAGE:**
1. **`claude_usage_stats`** - Claude.ai manual upload only
   - Source: Manual CSV/audit log upload
   - Conversation/project counts

2. **`claude_code_usage_stats`** - IF we can get /claude_code working
   - Source: Claude Admin API /claude_code
   - Engineering productivity metrics

3. **`cursor_usage_stats`** - Cursor productivity
   - Source: Cursor API
   - Engineering productivity metrics

**For API USAGE:**
- Combine into `claude_total_expenses` OR
- Try to filter using api_key_id patterns IF we can create mapping

## Next Investigation Steps

1. **Test workspace_id parameter** - Can we filter Cost Report by workspace?
2. **Check if newer API versions** have better metadata
3. **Contact Anthropic support** - Ask if there's a way to get platform breakdown
4. **Accept limitation** - Focus on what we CAN measure accurately

## User Attribution Strategy

Since workspace_id is null, we need to use:
- **api_key_id** from Usage Report (if available)
- Map api_key_id → user_email via Google Sheets
- Manual mapping table maintained by admin

**Question:** Can we at least get api_key_id to be non-null for user attribution?

---

**Recommendation:** Let's test if we can pass workspace_id as a parameter to filter the Cost Report, or if the null values are because we're querying all workspaces at once.
