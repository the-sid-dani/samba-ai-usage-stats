Account
Admin API
The Admin API lets you programmatically access your team's data, including member information, usage metrics, and spending details. Build custom dashboards, monitoring tools, or integrate with existing workflows.

The API is in its first release. We're expanding capabilities based on feedback - let us know what endpoints you need!

Authentication
All API requests require authentication using an API key. Only team administrators can create and manage API keys.

API keys are tied to the organization, viewable by all admins, and are unaffected by the original creator's account status.

Creating an API Key
Navigate to cursor.com/dashboard → Settings tab → Advanced → Admin API Keys
Click Create New API Key
Give your key a descriptive name (e.g., "Usage Dashboard Integration")
Copy the generated key immediately - you won't see it again
Format: key_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

Using Your API Key
Use your API key as the username in basic authentication:

Using curl with basic auth:


curl https://api.cursor.com/{route} -u API_KEY:
Or set the Authorization header directly:


Authorization: Basic {base64_encode('API_KEY:')}
Base URL
All API endpoints use:


https://api.cursor.com
Rate Limits
API requests are rate limited per team per endpoint to ensure platform stability. Rate limits apply to the team associated with your API key.

Rate-Limited Endpoints
Endpoint(s)	Rate Limit	Notes
POST /teams/daily-usage-data	20 requests per minute	Team usage analytics
POST /teams/filtered-usage-events	20 requests per minute	Team usage events
POST /teams/usage	20 requests per minute	Team usage data
POST /teams/user-spend-limit	60 requests per minute	User spend limit management
GET /analytics/ai-code/commits	20 requests per minute	AI code analytics (Enterprise)
GET /analytics/ai-code/commits.csv	20 requests per minute	AI code analytics (Enterprise)
GET /analytics/ai-code/changes	20 requests per minute	AI code analytics (Enterprise)
GET /analytics/ai-code/changes.csv	20 requests per minute	AI code analytics (Enterprise)
Rate Limit Behavior
Scope: Rate limits apply per team, not per user or API key
Response: When exceeded, you'll receive a 429 Too Many Requests response
Reset: Rate limits reset every minute
Recommendation: Implement exponential backoff when rate limits are hit
Usage Data Aggregation
Important: All usage-related APIs aggregate data at the hourly level. This includes:

POST /teams/daily-usage-data
POST /teams/filtered-usage-events
POST /teams/usage
We recommend polling the endpoints at most once per hour.

Endpoints
Get Team Members
Retrieve all team members and their details.


GET /teams/members
Response
Returns an array of team member objects:


{
  teamMembers: {
    name: string;
    email: string;
    role: "owner" | "member" | "free-owner";
  }
  [];
}
Example Response

{
  "teamMembers": [
    {
      "name": "Alex",
      "email": "developer@company.com",
      "role": "member"
    },
    {
      "name": "Sam",
      "email": "admin@company.com",
      "role": "owner"
    }
  ]
}
Example Request

curl -X GET https://api.cursor.com/teams/members \
  -u YOUR_API_KEY:
Get Daily Usage Data
Retrieve detailed daily usage metrics for your team within a date range. Provides insights into code edits, AI assistance usage, and acceptance rates.


POST /teams/daily-usage-data
Request Body
Parameter	Type	Required	Description
startDate	number	Yes	Start date in epoch milliseconds
endDate	number	Yes	End date in epoch milliseconds
Date range cannot exceed 30 days. Make multiple requests for longer periods.

Response

{
  data: {
    date: number;
    isActive: boolean;
    totalLinesAdded: number;
    totalLinesDeleted: number;
    acceptedLinesAdded: number;
    acceptedLinesDeleted: number;
    totalApplies: number;
    totalAccepts: number;
    totalRejects: number;
    totalTabsShown: number;
    totalTabsAccepted: number;
    composerRequests: number;
    chatRequests: number;
    agentRequests: number;
    cmdkUsages: number;
    subscriptionIncludedReqs: number;
    apiKeyReqs: number;
    usageBasedReqs: number;
    bugbotUsages: number;
    mostUsedModel: string;
    applyMostUsedExtension?: string;
    tabMostUsedExtension?: string;
    clientVersion?: string;
    email?: string;
  }[];
  period: {
    startDate: number;
    endDate: number;
  };
}
Response Fields
Field	Description
date	Date in epoch milliseconds
isActive	User active on this day
totalLinesAdded	Lines of code added
totalLinesDeleted	Lines of code deleted
acceptedLinesAdded	Lines added from accepted AI suggestions
acceptedLinesDeleted	Lines deleted from accepted AI suggestions
totalApplies	Apply operations
totalAccepts	Accepted suggestions
totalRejects	Rejected suggestions
totalTabsShown	Tab completions shown
totalTabsAccepted	Tab completions accepted
composerRequests	Composer requests
chatRequests	Chat requests
agentRequests	Agent requests
cmdkUsages	Command palette (Cmd+K) uses
subscriptionIncludedReqs	Subscription requests
apiKeyReqs	API key requests
usageBasedReqs	Pay-per-use requests
bugbotUsages	Bug detection uses
mostUsedModel	Most frequent AI model
applyMostUsedExtension	Most used file extension for applies
tabMostUsedExtension	Most used file extension for tabs
clientVersion	Cursor version
email	User email
Example Response

{
  "data": [
    {
      "date": 1710720000000,
      "isActive": true,
      "totalLinesAdded": 1543,
      "totalLinesDeleted": 892,
      "acceptedLinesAdded": 1102,
      "acceptedLinesDeleted": 645,
      "totalApplies": 87,
      "totalAccepts": 73,
      "totalRejects": 14,
      "totalTabsShown": 342,
      "totalTabsAccepted": 289,
      "composerRequests": 45,
      "chatRequests": 128,
      "agentRequests": 12,
      "cmdkUsages": 67,
      "subscriptionIncludedReqs": 180,
      "apiKeyReqs": 0,
      "usageBasedReqs": 5,
      "bugbotUsages": 3,
      "mostUsedModel": "gpt-5",
      "applyMostUsedExtension": ".tsx",
      "tabMostUsedExtension": ".ts",
      "clientVersion": "0.25.1",
      "email": "developer@company.com"
    },
    {
      "date": 1710806400000,
      "isActive": true,
      "totalLinesAdded": 2104,
      "totalLinesDeleted": 1203,
      "acceptedLinesAdded": 1876,
      "acceptedLinesDeleted": 987,
      "totalApplies": 102,
      "totalAccepts": 91,
      "totalRejects": 11,
      "totalTabsShown": 456,
      "totalTabsAccepted": 398,
      "composerRequests": 67,
      "chatRequests": 156,
      "agentRequests": 23,
      "cmdkUsages": 89,
      "subscriptionIncludedReqs": 320,
      "apiKeyReqs": 15,
      "usageBasedReqs": 0,
      "bugbotUsages": 5,
      "mostUsedModel": "claude-3-opus",
      "applyMostUsedExtension": ".py",
      "tabMostUsedExtension": ".py",
      "clientVersion": "0.25.1",
      "email": "developer@company.com"
    }
  ],
  "period": {
    "startDate": 1710720000000,
    "endDate": 1710892800000
  }
}
Example Request

curl -X POST https://api.cursor.com/teams/daily-usage-data \
  -u YOUR_API_KEY: \
  -H "Content-Type: application/json" \
  -d '{
    "startDate": 1710720000000,
    "endDate": 1710892800000
  }'
Get Spending Data
Retrieve spending information for the current calendar month with search, sorting, and pagination.


POST /teams/spend
Request Body
Parameter	Type	Required	Description
searchTerm	string	No	Search in user names and emails
sortBy	string	No	Sort by: amount, date, user. Default: date
sortDirection	string	No	Sort direction: asc, desc. Default: desc
page	number	No	Page number (1-indexed). Default: 1
pageSize	number	No	Results per page
Response

{
  teamMemberSpend: {
    spendCents: number;
    fastPremiumRequests: number;
    name: string;
    email: string;
    role: "owner" | "member" | "free-owner";
    hardLimitOverrideDollars: number;
  }
  [];
  subscriptionCycleStart: number;
  totalMembers: number;
  totalPages: number;
}
Response Fields
Field	Description
spendCents	Total spend in cents
fastPremiumRequests	Fast premium model requests
name	Member's name
email	Member's email
role	Team role
hardLimitOverrideDollars	Custom spending limit override
subscriptionCycleStart	Subscription cycle start (epoch milliseconds)
totalMembers	Total team members
totalPages	Total pages
Example Response

{
  "teamMemberSpend": [
    {
      "spendCents": 2450,
      "fastPremiumRequests": 1250,
      "name": "Alex",
      "email": "developer@company.com",
      "role": "member",
      "hardLimitOverrideDollars": 100
    },
    {
      "spendCents": 1875,
      "fastPremiumRequests": 980,
      "name": "Sam",
      "email": "admin@company.com",
      "role": "owner",
      "hardLimitOverrideDollars": 0
    }
  ],
  "subscriptionCycleStart": 1708992000000,
  "totalMembers": 15,
  "totalPages": 1
}
Example Requests
Basic spending data:


curl -X POST https://api.cursor.com/teams/spend \
  -u YOUR_API_KEY: \
  -H "Content-Type: application/json" \
  -d '{}'
Search specific user with pagination:


curl -X POST https://api.cursor.com/teams/spend \
  -u YOUR_API_KEY: \
  -H "Content-Type: application/json" \
  -d '{
    "searchTerm": "alex@company.com",
    "page": 2,
    "pageSize": 25
  }'
Get Usage Events Data
Retrieve detailed usage events for your team with comprehensive filtering, search, and pagination options. This endpoint provides granular insights into individual API calls, model usage, token consumption, and costs.

POST /teams/filtered-usage-events
Request Body
Parameter	Type	Required	Description
startDate	number	No	Start date in epoch milliseconds
endDate	number	No	End date in epoch milliseconds
userId	number	No	Filter by specific user ID
page	number	No	Page number (1-indexed). Default: 1
pageSize	number	No	Number of results per page. Default: 10
email	string	No	Filter by user email address
Response

{
  totalUsageEventsCount: number;
  pagination: {
    numPages: number;
    currentPage: number;
    pageSize: number;
    hasNextPage: boolean;
    hasPreviousPage: boolean;
  };
  usageEvents: {
    timestamp: string;
    model: string;
    kind: string;
    maxMode: boolean;
    requestsCosts: number;
    isTokenBasedCall: boolean;
    tokenUsage?: {
      inputTokens: number;
      outputTokens: number;
      cacheWriteTokens: number;
      cacheReadTokens: number;
      totalCents: number;
    };
    isFreeBugbot: boolean;
    userEmail: string;
  }[];
  period: {
    startDate: number;
    endDate: number;
  };
}
Response Fields Explained
Field	Description
totalUsageEventsCount	Total number of usage events matching the query
pagination	Pagination metadata for navigating results
timestamp	Event timestamp in epoch milliseconds
model	AI model used for the request
kind	Usage category (e.g., "Usage-based", "Included in Business")
maxMode	Whether max mode was enabled
requestsCosts	Cost in request units
isTokenBasedCall	True when the event is charged as a usage-based event
tokenUsage	Detailed token consumption (available when isTokenBasedCall is true)
isFreeBugbot	Whether this was a free bugbot usage
userEmail	Email of the user who made the request
period	Date range of the queried data
Example Response

{
  "totalUsageEventsCount": 113,
  "pagination": {
    "numPages": 12,
    "currentPage": 1,
    "pageSize": 10,
    "hasNextPage": true,
    "hasPreviousPage": false
  },
  "usageEvents": [
    {
      "timestamp": "1750979225854",
      "model": "claude-4-opus",
      "kind": "Usage-based",
      "maxMode": true,
      "requestsCosts": 5,
      "isTokenBasedCall": true,
      "tokenUsage": {
        "inputTokens": 126,
        "outputTokens": 450,
        "cacheWriteTokens": 6112,
        "cacheReadTokens": 11964,
        "totalCents": 20.18232
      },
      "isFreeBugbot": false,
      "userEmail": "developer@company.com"
    },
    {
      "timestamp": "1750979173824",
      "model": "claude-4-opus",
      "kind": "Usage-based",
      "maxMode": true,
      "requestsCosts": 10,
      "isTokenBasedCall": true,
      "tokenUsage": {
        "inputTokens": 5805,
        "outputTokens": 311,
        "cacheWriteTokens": 11964,
        "cacheReadTokens": 0,
        "totalCents": 40.16699999999999
      },
      "isFreeBugbot": false,
      "userEmail": "developer@company.com"
    },
    {
      "timestamp": "1750978339901",
      "model": "claude-4-sonnet-thinking",
      "kind": "Included in Business",
      "maxMode": true,
      "requestsCosts": 1.4,
      "isTokenBasedCall": false,
      "isFreeBugbot": false,
      "userEmail": "admin@company.com"
    }
  ],
  "period": {
    "startDate": 1748411762359,
    "endDate": 1751003762359
  }
}
Example Requests
Get all usage events with default pagination:


curl -X POST https://api.cursor.com/teams/filtered-usage-events \
  -u YOUR_API_KEY: \
  -H "Content-Type: application/json" \
  -d '{}'
Filter by date range and specific user:


curl -X POST https://api.cursor.com/teams/filtered-usage-events \
  -u YOUR_API_KEY: \
  -H "Content-Type: application/json" \
  -d '{
    "startDate": 1748411762359,
    "endDate": 1751003762359,
    "email": "developer@company.com",
    "page": 1,
    "pageSize": 25
  }'
Get usage events for a specific user with custom pagination:


curl -X POST https://api.cursor.com/teams/filtered-usage-events \
  -u YOUR_API_KEY: \
  -H "Content-Type: application/json" \
  -d '{
    "userId": 12345,
    "page": 2,
    "pageSize": 50
  }'
Set User Spend Limit
Set spending limits for individual team members. This allows you to control how much each user can spend on AI usage within your team.

POST /teams/user-spend-limit
Rate limiting: 60 requests per minute per team

Request Body
Parameter	Type	Required	Description
userEmail	string	Yes	Email address of the team member
spendLimitDollars	number	Yes	Spending limit in dollars (integer only, no decimals).
The user must already be a member of your team
Only integer values are accepted (no decimal amounts)
Setting spendLimitDollars to 0 will set the limit to $0
Response
Returns a standardized response indicating success or failure:


{
  outcome: 'success' | 'error';
  message: string;
}
Example Responses
Successfully set a limit:


{
  "outcome": "success",
  "message": "Spend limit set to $100 for user developer@company.com"
}
Error response:


{
  "outcome": "error",
  "message": "Invalid email format"
}
Example Requests
Set a spending limit:


curl -X POST https://api.cursor.com/teams/user-spend-limit \
  -u YOUR_API_KEY: \
  -H "Content-Type: application/json" \
  -d '{
    "userEmail": "developer@company.com",
    "spendLimitDollars": 100
  }'
Repo Blocklists API
Add repositories and use patterns to prevent files or directories from being indexed or used as context for your team.

Get Team Repo Blocklists
Retrieve all repository blocklists configured for your team.

GET /settings/repo-blocklists/repos
Response
Returns an array of repository blocklist objects:


{
  repos: {
    id: string;
    url: string;
    patterns: string[];
  }[];
}
Example Response

{
  "repos": [
    {
      "id": "repo_123",
      "url": "https://github.com/company/sensitive-repo",
      "patterns": ["*.env", "config/*", "secrets/**"]
    },
    {
      "id": "repo_456",
      "url": "https://github.com/company/internal-tools",
      "patterns": ["*"]
    }
  ]
}
Example Request

curl -X GET https://api.cursor.com/settings/repo-blocklists/repos \
  -u YOUR_API_KEY:
Upsert Repo Blocklists
Replace existing repository blocklists for the provided repos. Note: This endpoint will only overwrite the patterns for the repositories provided. All other repos will be unaffected.

POST /settings/repo-blocklists/repos/upsert
Request Body
Parameter	Type	Required	Description
repos	array	Yes	Array of repository blocklist objects
Each repository object must contain:

Field	Type	Required	Description
url	string	Yes	Repository URL to blocklist
patterns	string[]	Yes	Array of file patterns to block (glob patterns supported)
Response
Returns the updated list of repository blocklists:


{
  repos: {
    id: string;
    url: string;
    patterns: string[];
  }[];
}
Example Request

curl -X POST https://api.cursor.com/settings/repo-blocklists/repos/upsert \
  -u YOUR_API_KEY: \
  -H "Content-Type: application/json" \
  -d '{
    "repos": [
      {
        "url": "https://github.com/company/sensitive-repo",
        "patterns": ["*.env", "config/*", "secrets/**"]
      },
      {
        "url": "https://github.com/company/internal-tools",
        "patterns": ["*"]
      }
    ]
  }'
Delete Repo Blocklist
Remove a specific repository from the blocklist.

DELETE /settings/repo-blocklists/repos/:repoId
Parameters
Parameter	Type	Required	Description
repoId	string	Yes	ID of the repository blocklist to delete
Response
Returns 204 No Content on successful deletion.

Example Request

curl -X DELETE https://api.cursor.com/settings/repo-blocklists/repos/repo_123 \
  -u YOUR_API_KEY:
Pattern Examples
Common blocklist patterns:

* - Block entire repository
*.env - Block all .env files
config/* - Block all files in config directory
**/*.secret - Block all .secret files in any subdirectory
src/api/keys.ts - Block specific file