# External API Integrations

## Anthropic Claude API Integration

**Purpose:** Fetch usage and cost data for Claude API, Claude Code, and Claude.ai platforms
**Documentation:** https://docs.anthropic.com/en/api/usage-report
**Base URL:** `https://api.anthropic.com/v1`
**Authentication:** Admin API key with x-api-key header
**Rate Limits:** Not specified - implement exponential backoff strategy

**Key Endpoints Used:**
- `GET /organizations/usage_report/messages` - Daily usage data with token counts and model usage
- `GET /organizations/cost_report` - Daily cost breakdown by workspace

**Integration Notes:**
- API key ID to user email mapping required via Google Sheets
- Pagination handling for large date ranges
- 31-day maximum query limit requires chunked requests for historical data

## Cursor Admin API Integration

**Purpose:** Fetch team usage data including lines of code and productivity metrics
**Documentation:** Cursor admin portal documentation
**Base URL:** `https://api.cursor.com`
**Authentication:** Bearer token in Authorization header
**Rate Limits:** 90-day maximum date range per request

**Key Endpoints Used:**
- `GET /teams/daily-usage-data` - Daily team usage with developer attribution and code metrics

**Integration Notes:**
- Direct email attribution (no additional mapping required)
- Unix timestamp format requires conversion to standard dates
- Client version tracking available for tool adoption analysis

## Google Sheets API Integration

**Purpose:** Manual API key to user email mapping for cost attribution
**Documentation:** https://developers.google.com/sheets/api
**Authentication:** Service account with Sheets API access
**Range:** `Sheet1!A:C` for key mapping data

**Key Endpoints Used:**
- `GET /spreadsheets/{spreadsheetId}/values/{range}` - Fetch API key mappings

**Integration Notes:**
- Manual maintenance by finance team
- Three-column format: api_key_name, email, description
- Validation logic needed for email format and active user verification

---
