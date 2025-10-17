# Cursor API Specification

## Overview

The Cursor Admin API provides comprehensive coding productivity metrics with direct email attribution and hybrid cost model for team usage analytics.

## Authentication

**Method:** HTTP Basic Authentication
**Format:** API key as username, empty password
**Header:** `Authorization: Basic {base64(api_key:)}`

```python
# Example authentication
response = requests.post(
    url,
    auth=(api_key, ""),  # API key as username, empty password
    headers={"Content-Type": "application/json"},
    json=data
)
```

## Endpoint

**URL:** `https://api.cursor.com/teams/daily-usage-data`
**Method:** POST
**Rate Limits:** 90-day maximum date range per request

## Request Format

```json
{
  "startDate": 1704067200000,  // Unix timestamp in milliseconds
  "endDate": 1711929600000     // Unix timestamp in milliseconds
}
```

**Date Range Constraints:**
- Maximum range: 90 days
- Timestamps must be in milliseconds (JavaScript format)
- Start date must be before end date

## Response Schema

```typescript
interface CursorUsageResponse {
  data: Array<{
    // User Attribution
    email: string;                    // Direct user email (no mapping needed)
    date: string | number;            // Date (string or Unix timestamp)
    isActive: boolean;                // User activity flag

    // Productivity Metrics
    totalLinesAdded: number;          // Lines suggested by AI
    totalLinesDeleted: number;        // Lines deleted with AI help
    acceptedLinesAdded: number;       // Lines accepted by developer
    acceptedLinesDeleted: number;     // Accepted deletions

    // AI Interaction Metrics
    totalApplies: number;             // AI suggestions applied
    totalAccepts: number;             // AI suggestions accepted
    totalRejects: number;             // AI suggestions rejected
    totalTabsShown: number;           // Tab completion suggestions
    totalTabsAccepted: number;        // Tab completions accepted

    // Request Type Breakdown
    composerRequests: number;         // Long-form code generation
    chatRequests: number;             // Q&A with AI
    agentRequests: number;            // Autonomous code changes
    cmdkUsages: number;               // Cmd+K inline requests

    // Cost Attribution
    subscriptionIncludedReqs: number; // Within subscription limit (≤500)
    usageBasedReqs: number;           // Beyond subscription (overage)
    apiKeyReqs: number;               // Direct API usage

    // Context Data
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

## Available Metrics

### Productivity Metrics
- `totalLinesAdded` - Total lines suggested by Cursor AI
- `totalLinesDeleted` - Total lines deleted with AI assistance
- `acceptedLinesAdded` - Lines of code accepted by developer
- `acceptedLinesDeleted` - Deleted lines accepted by developer

**Usage:** Calculate acceptance rate, productivity impact

### AI Interaction Metrics
- `totalApplies` - Number of AI suggestions applied
- `totalAccepts` - Number of AI suggestions accepted
- `totalRejects` - Number of AI suggestions rejected
- `totalTabsShown` - Tab completion suggestions displayed
- `totalTabsAccepted` - Tab completion suggestions accepted

**Usage:** Measure AI effectiveness, user engagement

### Request Type Breakdown
- `composerRequests` - Long-form code generation requests
- `chatRequests` - Q&A interactions with AI
- `agentRequests` - Autonomous code modification requests
- `cmdkUsages` - Inline Cmd+K quick edit requests

**Usage:** Understand usage patterns, feature adoption

### Cost Attribution
- `subscriptionIncludedReqs` - Requests within subscription (≤500/month)
- `usageBasedReqs` - Overage requests (pay-per-use)
- `apiKeyReqs` - Direct API key usage

**Usage:** Cost allocation, budget forecasting

### Context Data
- `mostUsedModel` - Primary AI model used (e.g., "gpt-4")
- `clientVersion` - Cursor IDE version
- `applyMostUsedExtension` - Most common file type for applies
- `tabMostUsedExtension` - Most common file type for tabs

**Usage:** Technology stack analysis, version tracking

## Cost Model

Cursor uses a hybrid pricing model:

1. **Subscription Base** - 500 requests/month included
2. **Usage-Based Overage** - Pay-per-request beyond 500
3. **API Key Usage** - Direct API consumption

**Cost Calculation:**
```
total_cost = (subscription_cost) + (usage_based_reqs × overage_rate) + (api_key_reqs × api_rate)
```

## Attribution Confidence

**Confidence Level:** HIGH
**Attribution Method:** Direct email in API response
**No Mapping Required:** Email field directly identifies user

This is the highest confidence attribution available across all platforms (Claude, Cursor, etc.)

## Example Implementation

```python
import requests
from datetime import datetime, timedelta

class CursorClient:
    BASE_URL = "https://api.cursor.com"
    MAX_DATE_RANGE_DAYS = 90

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_daily_usage_data(self, start_date: datetime, end_date: datetime):
        """Fetch daily usage data for date range."""
        # Validate date range
        if (end_date - start_date).days >= self.MAX_DATE_RANGE_DAYS:
            raise ValueError("Date range cannot exceed 90 days")

        # Convert to milliseconds
        start_ms = int(start_date.timestamp() * 1000)
        end_ms = int(end_date.timestamp() * 1000)

        # Make request
        response = requests.post(
            f"{self.BASE_URL}/teams/daily-usage-data",
            auth=(self.api_key, ""),
            headers={"Content-Type": "application/json"},
            json={"startDate": start_ms, "endDate": end_ms},
            timeout=30
        )

        response.raise_for_status()
        return response.json()

# Usage
client = CursorClient(api_key="your-api-key")
data = client.get_daily_usage_data(
    start_date=datetime.now() - timedelta(days=7),
    end_date=datetime.now()
)
```

## Error Handling

**Common Error Codes:**
- `400` - Invalid request (check date format, range)
- `401` - Authentication failed (invalid API key)
- `429` - Rate limited (wait and retry)
- `500` - Server error (retry with backoff)

**Best Practices:**
- Implement exponential backoff for retries
- Validate date ranges before requests
- Log failed requests for debugging
- Monitor API response times

## Data Retention

Cursor retains usage data for historical analysis. Exact retention period should be confirmed with Cursor support.

## API Changes

This specification reflects the API as of January 2025. Check Cursor's official documentation for updates.
