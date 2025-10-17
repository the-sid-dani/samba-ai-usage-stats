# AI Cost Allocation Architecture

## Cost Categories Matching Platform Categories

### 1. AI Coding Agents Cost Allocation
**Join Pattern**: `fact_cursor_daily_usage + fact_claude_daily_usage (claude_code platform only)`
**Cost Types**:
- Cursor: subscription_cost + overage_cost (lines-based productivity)
- Claude Code: token_cost (IDE integration, tool usage)
**ROI Metric**: Total cost / Total lines of code output
**Business Purpose**: Engineering team budget allocation

### 2. API Usage Cost Allocation  
**Join Pattern**: `fact_cursor_daily_usage (API reqs) + fact_claude_daily_usage (claude_api platform only)`
**Cost Types**:
- Cursor API: usage_based_reqs overage cost (beyond subscription)
- Claude API: pure token consumption cost
**ROI Metric**: Total cost / Total tokens or API requests
**Business Purpose**: Direct API consumption tracking

### 3. AI Assistants Cost Allocation
**Join Pattern**: `fact_claude_daily_usage (claude_ai platform only) + future platforms`
**Cost Types**:
- claude.ai: subscription + usage costs (conversation-based)
- Future Gemini: API/subscription costs
- Future ChatGPT: API/subscription costs  
**ROI Metric**: Total cost / Total conversations or projects
**Business Purpose**: Knowledge worker productivity investment

## Key Principle: NO CROSS-CATEGORY COST MIXING
- Don't add claude_api costs to coding agent costs
- Don't compare token costs with lines-of-code costs
- Maintain separate ROI calculations per category
- Executive view can show total investment across categories