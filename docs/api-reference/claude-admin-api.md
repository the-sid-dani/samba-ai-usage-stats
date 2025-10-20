# Admin API overview

<Tip>
  **The Admin API is unavailable for individual accounts.** To collaborate with teammates and add members, set up your organization in **Console → Settings → Organization**.
</Tip>

The [Admin API](/en/api/admin-api) allows you to programmatically manage your organization's resources, including organization members, workspaces, and API keys. This provides programmatic control over administrative tasks that would otherwise require manual configuration in the [Claude Console](https://console.anthropic.com).

<Check>
  **The Admin API requires special access**

  The Admin API requires a special Admin API key (starting with `sk-ant-admin...`) that differs from standard API keys. Only organization members with the admin role can provision Admin API keys through the Claude Console.
</Check>

## How the Admin API works

When you use the Admin API:

1. You make requests using your Admin API key in the `x-api-key` header
2. The API allows you to manage:
   * Organization members and their roles
   * Organization member invites
   * Workspaces and their members
   * API keys

This is useful for:

* Automating user onboarding/offboarding
* Programmatically managing workspace access
* Monitoring and managing API key usage

## Organization roles and permissions

There are five organization-level roles. See more details [here](https://support.claude.com/en/articles/10186004-api-console-roles-and-permissions).

| Role               | Permissions                                                        |
| ------------------ | ------------------------------------------------------------------ |
| user               | Can use Workbench                                                  |
| claude\_code\_user | Can use Workbench and [Claude Code](/en/docs/claude-code/overview) |
| developer          | Can use Workbench and manage API keys                              |
| billing            | Can use Workbench and manage billing details                       |
| admin              | Can do all of the above, plus manage users                         |

## Key concepts

### Organization Members

You can list [organization members](/en/api/admin-api/users/get-user), update member roles, and remove members.

<CodeGroup>
  ```bash Shell theme={null}
  # List organization members
  curl "https://api.anthropic.com/v1/organizations/users?limit=10" \
    --header "anthropic-version: 2023-06-01" \
    --header "x-api-key: $ANTHROPIC_ADMIN_KEY"

  # Update member role
  curl "https://api.anthropic.com/v1/organizations/users/{user_id}" \
    --header "anthropic-version: 2023-06-01" \
    --header "x-api-key: $ANTHROPIC_ADMIN_KEY" \
    --data '{"role": "developer"}'

  # Remove member
  curl --request DELETE "https://api.anthropic.com/v1/organizations/users/{user_id}" \
    --header "anthropic-version: 2023-06-01" \
    --header "x-api-key: $ANTHROPIC_ADMIN_KEY"
  ```
</CodeGroup>

### Organization Invites

You can invite users to organizations and manage those [invites](/en/api/admin-api/invites/get-invite).

<CodeGroup>
  ```bash Shell theme={null}
  # Create invite
  curl --request POST "https://api.anthropic.com/v1/organizations/invites" \
    --header "anthropic-version: 2023-06-01" \
    --header "x-api-key: $ANTHROPIC_ADMIN_KEY" \
    --data '{
      "email": "newuser@domain.com",
      "role": "developer"
    }'

  # List invites
  curl "https://api.anthropic.com/v1/organizations/invites?limit=10" \
    --header "anthropic-version: 2023-06-01" \
    --header "x-api-key: $ANTHROPIC_ADMIN_KEY"

  # Delete invite
  curl --request DELETE "https://api.anthropic.com/v1/organizations/invites/{invite_id}" \
    --header "anthropic-version: 2023-06-01" \
    --header "x-api-key: $ANTHROPIC_ADMIN_KEY"
  ```
</CodeGroup>

### Workspaces

Create and manage [workspaces](/en/api/admin-api/workspaces/get-workspace) ([console](https://console.anthropic.com/settings/workspaces)) to organize your resources:

<CodeGroup>
  ```bash Shell theme={null}
  # Create workspace
  curl --request POST "https://api.anthropic.com/v1/organizations/workspaces" \
    --header "anthropic-version: 2023-06-01" \
    --header "x-api-key: $ANTHROPIC_ADMIN_KEY" \
    --data '{"name": "Production"}'

  # List workspaces
  curl "https://api.anthropic.com/v1/organizations/workspaces?limit=10&include_archived=false" \
    --header "anthropic-version: 2023-06-01" \
    --header "x-api-key: $ANTHROPIC_ADMIN_KEY"

  # Archive workspace
  curl --request POST "https://api.anthropic.com/v1/organizations/workspaces/{workspace_id}/archive" \
    --header "anthropic-version: 2023-06-01" \
    --header "x-api-key: $ANTHROPIC_ADMIN_KEY"
  ```
</CodeGroup>

### Workspace Members

Manage [user access to specific workspaces](/en/api/admin-api/workspace_members/get-workspace-member):

<CodeGroup>
  ```bash Shell theme={null}
  # Add member to workspace
  curl --request POST "https://api.anthropic.com/v1/organizations/workspaces/{workspace_id}/members" \
    --header "anthropic-version: 2023-06-01" \
    --header "x-api-key: $ANTHROPIC_ADMIN_KEY" \
    --data '{
      "user_id": "user_xxx",
      "workspace_role": "workspace_developer"
    }'

  # List workspace members
  curl "https://api.anthropic.com/v1/organizations/workspaces/{workspace_id}/members?limit=10" \
    --header "anthropic-version: 2023-06-01" \
    --header "x-api-key: $ANTHROPIC_ADMIN_KEY"

  # Update member role
  curl --request POST "https://api.anthropic.com/v1/organizations/workspaces/{workspace_id}/members/{user_id}" \
    --header "anthropic-version: 2023-06-01" \
    --header "x-api-key: $ANTHROPIC_ADMIN_KEY" \
    --data '{
      "workspace_role": "workspace_admin"
    }'

  # Remove member from workspace
  curl --request DELETE "https://api.anthropic.com/v1/organizations/workspaces/{workspace_id}/members/{user_id}" \
    --header "anthropic-version: 2023-06-01" \
    --header "x-api-key: $ANTHROPIC_ADMIN_KEY"
  ```
</CodeGroup>

### API Keys

Monitor and manage [API keys](/en/api/admin-api/apikeys/get-api-key):

<CodeGroup>
  ```bash Shell theme={null}
  # List API keys
  curl "https://api.anthropic.com/v1/organizations/api_keys?limit=10&status=active&workspace_id=wrkspc_xxx" \
    --header "anthropic-version: 2023-06-01" \
    --header "x-api-key: $ANTHROPIC_ADMIN_KEY"

  # Update API key
  curl --request POST "https://api.anthropic.com/v1/organizations/api_keys/{api_key_id}" \
    --header "anthropic-version: 2023-06-01" \
    --header "x-api-key: $ANTHROPIC_ADMIN_KEY" \
    --data '{
      "status": "inactive",
      "name": "New Key Name"
    }'
  ```
</CodeGroup>

## Accessing organization info

Get information about your organization programmatically with the `/v1/organizations/me` endpoint.

For example:

```bash  theme={null}
curl "https://api.anthropic.com/v1/organizations/me" \
  --header "anthropic-version: 2023-06-01" \
  --header "x-api-key: $ADMIN_API_KEY"
```

```json  theme={null}
{
  "id": "12345678-1234-5678-1234-567812345678",
  "type": "organization",
  "name": "Organization Name"
}
```

This endpoint is useful for programmatically determining which organization an Admin API key belongs to.

For complete parameter details and response schemas, see the [Organization Info API reference](/en/api/admin-api/organization/get-me).

## Accessing usage and cost reports

To access usage and cost reports for your organization, use the Usage and Cost API endpoints:

* The [**Usage endpoint**](/en/api/usage-cost-api#usage-api) (`/v1/organizations/usage_report/messages`) provides detailed usage data, including token counts and request metrics, grouped by various dimensions such as workspace, user, and model.
* The [**Cost endpoint**](/en/api/usage-cost-api#cost-api) (`/v1/organizations/cost_report`) provides cost data associated with your organization's usage, allowing you to track expenses and allocate costs by workspace or description.

These endpoints provide detailed insights into your organization's usage and associated costs.

## Accessing Claude Code analytics

For organizations using Claude Code, the [**Claude Code Analytics API**](/en/api/claude-code-analytics-api) provides detailed productivity metrics and usage insights:

* The [**Claude Code Analytics endpoint**](/en/api/claude-code-analytics-api) (`/v1/organizations/usage_report/claude_code`) provides daily aggregated metrics for Claude Code usage, including sessions, lines of code, commits, pull requests, tool usage statistics, and cost data broken down by user and model.

This API enables you to track developer productivity, analyze Claude Code adoption, and build custom dashboards for your organization.

## Best practices

To effectively use the Admin API:

* Use meaningful names and descriptions for workspaces and API keys
* Implement proper error handling for failed operations
* Regularly audit member roles and permissions
* Clean up unused workspaces and expired invites
* Monitor API key usage and rotate keys periodically

## FAQ

<AccordionGroup>
  <Accordion title="What permissions are needed to use the Admin API?">
    Only organization members with the admin role can use the Admin API. They must also have a special Admin API key (starting with `sk-ant-admin`).
  </Accordion>

  <Accordion title="Can I create new API keys through the Admin API?">
    No, new API keys can only be created through the Claude Console for security reasons. The Admin API can only manage existing API keys.
  </Accordion>

  <Accordion title="What happens to API keys when removing a user?">
    API keys persist in their current state as they are scoped to the Organization, not to individual users.
  </Accordion>

  <Accordion title="Can organization admins be removed via the API?">
    No, organization members with the admin role cannot be removed via the API for security reasons.
  </Accordion>

  <Accordion title="How long do organization invites last?">
    Organization invites expire after 21 days. There is currently no way to modify this expiration period.
  </Accordion>

  <Accordion title="Are there limits on workspaces?">
    Yes, you can have a maximum of 100 workspaces per Organization. Archived workspaces do not count towards this limit.
  </Accordion>

  <Accordion title="What's the Default Workspace?">
    Every Organization has a "Default Workspace" that cannot be edited or removed, and has no ID. This Workspace does not appear in workspace list endpoints.
  </Accordion>

  <Accordion title="How do organization roles affect Workspace access?">
    Organization admins automatically get the `workspace_admin` role to all workspaces. Organization billing members automatically get the `workspace_billing` role. Organization users and developers must be manually added to each workspace.
  </Accordion>

  <Accordion title="Which roles can be assigned in workspaces?">
    Organization users and developers can be assigned `workspace_admin`, `workspace_developer`, or `workspace_user` roles. The `workspace_billing` role can't be manually assigned - it's inherited from having the organization `billing` role.
  </Accordion>

  <Accordion title="Can organization admin or billing members' workspace roles be changed?">
    Only organization billing members can have their workspace role upgraded to an admin role. Otherwise, organization admins and billing members can't have their workspace roles changed or be removed from workspaces while they hold those organization roles. Their workspace access must be modified by changing their organization role first.
  </Accordion>

  <Accordion title="What happens to workspace access when organization roles change?">
    If an organization admin or billing member is demoted to user or developer, they lose access to all workspaces except ones where they were manually assigned roles. When users are promoted to admin or billing roles, they gain automatic access to all workspaces.
  </Accordion>
</AccordionGroup>

# Usage and Cost API

> Programmatically access your organization's API usage and cost data with the Usage & Cost Admin API.

<Tip>
  **The Admin API is unavailable for individual accounts.** To collaborate with teammates and add members, set up your organization in **Console → Settings → Organization**.
</Tip>

The Usage & Cost Admin API provides programmatic and granular access to historical API usage and cost data for your organization. This data is similar to the information available in the [Usage](https://console.anthropic.com/usage) and [Cost](https://console.anthropic.com/cost) pages of the Claude Console.

This API enables you to better monitor, analyze, and optimize your Claude implementations:

* **Accurate Usage Tracking:** Get precise token counts and usage patterns instead of relying solely on response token counting
* **Cost Reconciliation:** Match internal records with Anthropic billing for finance and accounting teams
* **Product performance and improvement:** Monitor product performance while measuring if changes to the system have improved it, or setup alerting
* **[Rate limit](/en/api/rate-limits) and [Priority Tier](/en/api/service-tiers#get-started-with-priority-tier) optimization:** Optimize features like [prompt caching](/en/docs/build-with-claude/prompt-caching) or specific prompts to make the most of one’s allocated capacity, or purchase dedicated capacity.
* **Advanced Analysis:** Perform deeper data analysis than what's available in Console

<Check>
  **Admin API key required**

  This API is part of the [Admin API](/en/api/administration-api). These endpoints require an Admin API key (starting with `sk-ant-admin...`) that differs from standard API keys. Only organization members with the admin role can provision Admin API keys through the [Claude Console](https://console.anthropic.com/settings/admin-keys).
</Check>

## Partner solutions

Leading observability platforms offer ready-to-use integrations for monitoring your Claude API usage and cost, without writing custom code. These integrations provide dashboards, alerting, and analytics to help you manage your API usage effectively.

<CardGroup cols={3}>
  <Card title="Datadog" icon="chart-line" href="https://docs.datadoghq.com/integrations/anthropic/">
    LLM Observability with automatic tracing and monitoring
  </Card>

  <Card title="Grafana Cloud" icon="chart-area" href="https://grafana.com/docs/grafana-cloud/monitor-infrastructure/integrations/integration-reference/integration-anthropic/">
    Agentless integration for easy LLM observability with out-of-the-box dashboards and alerts
  </Card>

  <Card title="Honeycomb" icon="hexagon" href="https://docs.honeycomb.io/integrations/anthropic-usage-monitoring/">
    Advanced querying and visualization through OpenTelemetry
  </Card>
</CardGroup>

## Quick start

Get your organization's daily usage for the last 7 days:

```bash  theme={null}
curl "https://api.anthropic.com/v1/organizations/usage_report/messages?\
starting_at=2025-01-08T00:00:00Z&\
ending_at=2025-01-15T00:00:00Z&\
bucket_width=1d" \
  --header "anthropic-version: 2023-06-01" \
  --header "x-api-key: $ADMIN_API_KEY"
```

<Tip>
  **Set a User-Agent header for integrations**

  If you're building an integration, set your User-Agent header to help us understand usage patterns:

  ```
  User-Agent: YourApp/1.0.0 (https://yourapp.com)
  ```
</Tip>

## Usage API

Track token consumption across your organization with detailed breakdowns by model, workspace, and service tier with the `/v1/organizations/usage_report/messages` endpoint.

### Key concepts

* **Time buckets**: Aggregate usage data in fixed intervals (`1m`, `1h`, or `1d`)
* **Token tracking**: Measure uncached input, cached input, cache creation, and output tokens
* **Filtering & grouping**: Filter by API key, workspace, model, service tier, or context window, and group results by these dimensions
* **Server tool usage**: Track usage of server-side tools like web search

For complete parameter details and response schemas, see the [Usage API reference](/en/api/admin-api/usage-cost/get-messages-usage-report).

### Basic examples

#### Daily usage by model

```bash  theme={null}
curl "https://api.anthropic.com/v1/organizations/usage_report/messages?\
starting_at=2025-01-01T00:00:00Z&\
ending_at=2025-01-08T00:00:00Z&\
group_by[]=model&\
bucket_width=1d" \
  --header "anthropic-version: 2023-06-01" \
  --header "x-api-key: $ADMIN_API_KEY"
```

#### Hourly usage with filtering

```bash  theme={null}
curl "https://api.anthropic.com/v1/organizations/usage_report/messages?\
starting_at=2025-01-15T00:00:00Z&\
ending_at=2025-01-15T23:59:59Z&\
models[]=claude-sonnet-4-5-20250929&\
service_tiers[]=batch&\
context_window[]=0-200k&\
bucket_width=1h" \
  --header "anthropic-version: 2023-06-01" \
  --header "x-api-key: $ADMIN_API_KEY"
```

#### Filter usage by API keys and workspaces

```bash  theme={null}
curl "https://api.anthropic.com/v1/organizations/usage_report/messages?\
starting_at=2025-01-01T00:00:00Z&\
ending_at=2025-01-08T00:00:00Z&\
api_key_ids[]=apikey_01Rj2N8SVvo6BePZj99NhmiT&\
api_key_ids[]=apikey_01ABC123DEF456GHI789JKL&\
workspace_ids[]=wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ&\
workspace_ids[]=wrkspc_01XYZ789ABC123DEF456MNO&\
bucket_width=1d" \
  --header "anthropic-version: 2023-06-01" \
  --header "x-api-key: $ADMIN_API_KEY"
```

<Tip>
  To retrieve your organization's API key IDs, use the [List API Keys](/en/api/admin-api/apikeys/list-api-keys) endpoint.

  To retrieve your organization's workspace IDs, use the [List Workspaces](/en/api/admin-api/workspaces/list-workspaces) endpoint, or find your organization's workspace IDs in the Anthropic Console.
</Tip>

### Time granularity limits

| Granularity | Default Limit | Maximum Limit | Use Case               |
| ----------- | ------------- | ------------- | ---------------------- |
| `1m`        | 60 buckets    | 1440 buckets  | Real-time monitoring   |
| `1h`        | 24 buckets    | 168 buckets   | Daily patterns         |
| `1d`        | 7 buckets     | 31 buckets    | Weekly/monthly reports |

## Cost API

Retrieve service-level cost breakdowns in USD with the `/v1/organizations/cost_report` endpoint.

### Key concepts

* **Currency**: All costs in USD, reported as decimal strings in lowest units (cents)
* **Cost types**: Track token usage, web search, and code execution costs
* **Grouping**: Group costs by workspace or description for detailed breakdowns
* **Time buckets**: Daily granularity only (`1d`)

For complete parameter details and response schemas, see the [Cost API reference](/en/api/admin-api/usage-cost/get-cost-report).

<Warning>
  Priority Tier costs use a different billing model and are not included in the cost endpoint. Track Priority Tier usage through the usage endpoint instead.
</Warning>

### Basic example

```bash  theme={null}
curl "https://api.anthropic.com/v1/organizations/cost_report?\
starting_at=2025-01-01T00:00:00Z&\
ending_at=2025-01-31T00:00:00Z&\
group_by[]=workspace_id&\
group_by[]=description" \
  --header "anthropic-version: 2023-06-01" \
  --header "x-api-key: $ADMIN_API_KEY"
```

## Pagination

Both endpoints support pagination for large datasets:

1. Make your initial request
2. If `has_more` is `true`, use the `next_page` value in your next request
3. Continue until `has_more` is `false`

```bash  theme={null}
# First request
curl "https://api.anthropic.com/v1/organizations/usage_report/messages?\
starting_at=2025-01-01T00:00:00Z&\
ending_at=2025-01-31T00:00:00Z&\
limit=7" \
  --header "anthropic-version: 2023-06-01" \
  --header "x-api-key: $ADMIN_API_KEY"

# Response includes: "has_more": true, "next_page": "page_xyz..."

# Next request with pagination
curl "https://api.anthropic.com/v1/organizations/usage_report/messages?\
starting_at=2025-01-01T00:00:00Z&\
ending_at=2025-01-31T00:00:00Z&\
limit=7&\
page=page_xyz..." \
  --header "anthropic-version: 2023-06-01" \
  --header "x-api-key: $ADMIN_API_KEY"
```

## Common use cases

Explore detailed implementations in [anthropic-cookbook](https://github.com/anthropics/anthropic-cookbook):

* **Daily usage reports**: Track token consumption trends
* **Cost attribution**: Allocate expenses by workspace for chargebacks
* **Cache efficiency**: Measure and optimize prompt caching
* **Budget monitoring**: Set up alerts for spending thresholds
* **CSV export**: Generate reports for finance teams

## Frequently asked questions

### How fresh is the data?

Usage and cost data typically appears within 5 minutes of API request completion, though delays may occasionally be longer.

### What's the recommended polling frequency?

The API supports polling once per minute for sustained use. For short bursts (e.g., downloading paginated data), more frequent polling is acceptable. Cache results for dashboards that need frequent updates.

### How do I track code execution usage?

Code execution costs appear in the cost endpoint grouped under `Code Execution Usage` in the description field. Code execution is not included in the usage endpoint.

### How do I track Priority Tier usage?

Filter or group by `service_tier` in the usage endpoint and look for the `priority` value. Priority Tier costs are not available in the cost endpoint.

### What happens with Workbench usage?

API usage from the Workbench is not associated with an API key, so `api_key_id` will be `null` even when grouping by that dimension.

### How is the default workspace represented?

Usage and costs attributed to the default workspace have a `null` value for `workspace_id`.

### How do I get per-user cost breakdowns for Claude Code?

Use the [Claude Code Analytics API](/en/api/claude-code-analytics-api), which provides per-user estimated costs and productivity metrics without the performance limitations of breaking down costs by many API keys. For general API usage with many keys, use the [Usage API](#usage-api) to track token consumption as a cost proxy.

## See also

The Usage and Cost APIs can be used to help you deliver a better experience for your users, help you manage costs, and preserve your rate limit. Learn more about some of these other features:

* [Admin API overview](/en/api/administration-api)
* [Admin API reference](/en/api/admin-api)
* [Pricing](/en/docs/about-claude/pricing)
* [Prompt caching](/en/docs/build-with-claude/prompt-caching) - Optimize costs with caching
* [Batch processing](/en/docs/build-with-claude/batch-processing) - 50% discount on batch requests
* [Rate limits](/en/api/rate-limits) - Understand usage tiers

# Claude Code Analytics API

> Programmatically access your organization's Claude Code usage analytics and productivity metrics with the Claude Code Analytics Admin API.

<Tip>
  **The Admin API is unavailable for individual accounts.** To collaborate with teammates and add members, set up your organization in **Console → Settings → Organization**.
</Tip>

The Claude Code Analytics Admin API provides programmatic access to daily aggregated usage metrics for Claude Code users, enabling organizations to analyze developer productivity and build custom dashboards. This API bridges the gap between our basic [Analytics dashboard](https://console.anthropic.com/claude-code) and the complex OpenTelemetry integration.

This API enables you to better monitor, analyze, and optimize your Claude Code adoption:

* **Developer Productivity Analysis:** Track sessions, lines of code added/removed, commits, and pull requests created using Claude Code
* **Tool Usage Metrics:** Monitor acceptance and rejection rates for different Claude Code tools (Edit, Write, NotebookEdit)
* **Cost Analysis:** View estimated costs and token usage broken down by Claude model
* **Custom Reporting:** Export data to build executive dashboards and reports for management teams
* **Usage Justification:** Provide metrics to justify and expand Claude Code adoption internally

<Check>
  **Admin API key required**

  This API is part of the [Admin API](/en/api/administration-api). These endpoints require an Admin API key (starting with `sk-ant-admin...`) that differs from standard API keys. Only organization members with the admin role can provision Admin API keys through the [Claude Console](https://console.anthropic.com/settings/admin-keys).
</Check>

## Quick start

Get your organization's Claude Code analytics for a specific day:

```bash  theme={null}
curl "https://api.anthropic.com/v1/organizations/usage_report/claude_code?\
starting_at=2025-09-08&\
limit=20" \
  --header "anthropic-version: 2023-06-01" \
  --header "x-api-key: $ADMIN_API_KEY"
```

<Tip>
  **Set a User-Agent header for integrations**

  If you're building an integration, set your User-Agent header to help us understand usage patterns:

  ```
  User-Agent: YourApp/1.0.0 (https://yourapp.com)
  ```
</Tip>

## Claude Code Analytics API

Track Claude Code usage, productivity metrics, and developer activity across your organization with the `/v1/organizations/usage_report/claude_code` endpoint.

### Key concepts

* **Daily aggregation**: Returns metrics for a single day specified by the `starting_at` parameter
* **User-level data**: Each record represents one user's activity for the specified day
* **Productivity metrics**: Track sessions, lines of code, commits, pull requests, and tool usage
* **Token and cost data**: Monitor usage and estimated costs broken down by Claude model
* **Cursor-based pagination**: Handle large datasets with stable pagination using opaque cursors
* **Data freshness**: Metrics are available with up to 1-hour delay for consistency

For complete parameter details and response schemas, see the [Claude Code Analytics API reference](/en/api/admin-api/claude-code/get-claude-code-usage-report).

### Basic examples

#### Get analytics for a specific day

```bash  theme={null}
curl "https://api.anthropic.com/v1/organizations/usage_report/claude_code?\
starting_at=2025-09-08" \
  --header "anthropic-version: 2023-06-01" \
  --header "x-api-key: $ADMIN_API_KEY"
```

#### Get analytics with pagination

```bash  theme={null}
# First request
curl "https://api.anthropic.com/v1/organizations/usage_report/claude_code?\
starting_at=2025-09-08&\
limit=20" \
  --header "anthropic-version: 2023-06-01" \
  --header "x-api-key: $ADMIN_API_KEY"

# Subsequent request using cursor from response
curl "https://api.anthropic.com/v1/organizations/usage_report/claude_code?\
starting_at=2025-09-08&\
page=page_MjAyNS0wNS0xNFQwMDowMDowMFo=" \
  --header "anthropic-version: 2023-06-01" \
  --header "x-api-key: $ADMIN_API_KEY"
```

### Request parameters

| Parameter     | Type    | Required | Description                                                             |
| ------------- | ------- | -------- | ----------------------------------------------------------------------- |
| `starting_at` | string  | Yes      | UTC date in YYYY-MM-DD format. Returns metrics for this single day only |
| `limit`       | integer | No       | Number of records per page (default: 20, max: 1000)                     |
| `page`        | string  | No       | Opaque cursor token from previous response's `next_page` field          |

### Available metrics

Each response record contains the following metrics for a single user on a single day:

#### Dimensions

* **date**: Date in RFC 3339 format (UTC timestamp)
* **actor**: The user or API key that performed the Claude Code actions (either `user_actor` with `email_address` or `api_actor` with `api_key_name`)
* **organization\_id**: Organization UUID
* **customer\_type**: Type of customer account (`api` for API customers, `subscription` for Pro/Team customers)
* **terminal\_type**: Type of terminal or environment where Claude Code was used (e.g., `vscode`, `iTerm.app`, `tmux`)

#### Core metrics

* **num\_sessions**: Number of distinct Claude Code sessions initiated by this actor
* **lines\_of\_code.added**: Total number of lines of code added across all files by Claude Code
* **lines\_of\_code.removed**: Total number of lines of code removed across all files by Claude Code
* **commits\_by\_claude\_code**: Number of git commits created through Claude Code's commit functionality
* **pull\_requests\_by\_claude\_code**: Number of pull requests created through Claude Code's PR functionality

#### Tool action metrics

Breakdown of tool action acceptance and rejection rates by tool type:

* **edit\_tool.accepted/rejected**: Number of Edit tool proposals that the user accepted/rejected
* **write\_tool.accepted/rejected**: Number of Write tool proposals that the user accepted/rejected
* **notebook\_edit\_tool.accepted/rejected**: Number of NotebookEdit tool proposals that the user accepted/rejected

#### Model breakdown

For each Claude model used:

* **model**: Claude model identifier (e.g., `claude-3-5-sonnet-20241022`)
* **tokens.input/output**: Input and output token counts for this model
* **tokens.cache\_read/cache\_creation**: Cache-related token usage for this model
* **estimated\_cost.amount**: Estimated cost in cents USD for this model
* **estimated\_cost.currency**: Currency code for the cost amount (currently always `USD`)

### Response structure

The API returns data in the following format:

```json  theme={null}
{
  "data": [
    {
      "date": "2025-09-01T00:00:00Z",
      "actor": {
        "type": "user_actor",
        "email_address": "developer@company.com"
      },
      "organization_id": "dc9f6c26-b22c-4831-8d01-0446bada88f1",
      "customer_type": "api",
      "terminal_type": "vscode",
      "core_metrics": {
        "num_sessions": 5,
        "lines_of_code": {
          "added": 1543,
          "removed": 892
        },
        "commits_by_claude_code": 12,
        "pull_requests_by_claude_code": 2
      },
      "tool_actions": {
        "edit_tool": {
          "accepted": 45,
          "rejected": 5
        },
        "multi_edit_tool": {
          "accepted": 12,
          "rejected": 2
        },
        "write_tool": {
          "accepted": 8,
          "rejected": 1
        },
        "notebook_edit_tool": {
          "accepted": 3,
          "rejected": 0
        }
      },
      "model_breakdown": [
        {
          "model": "claude-3-5-sonnet-20241022",
          "tokens": {
            "input": 100000,
            "output": 35000,
            "cache_read": 10000,
            "cache_creation": 5000
          },
          "estimated_cost": {
            "currency": "USD",
            "amount": 1025
          }
        }
      ]
    }
  ],
  "has_more": false,
  "next_page": null
}
```

## Pagination

The API supports cursor-based pagination for organizations with large numbers of users:

1. Make your initial request with optional `limit` parameter
2. If `has_more` is `true` in the response, use the `next_page` value in your next request
3. Continue until `has_more` is `false`

The cursor encodes the position of the last record and ensures stable pagination even as new data arrives. Each pagination session maintains a consistent data boundary to ensure you don't miss or duplicate records.

## Common use cases

* **Executive dashboards**: Create high-level reports showing Claude Code impact on development velocity
* **AI tool comparison**: Export metrics to compare Claude Code with other AI coding tools like Copilot and Cursor
* **Developer productivity analysis**: Track individual and team productivity metrics over time
* **Cost tracking and allocation**: Monitor spending patterns and allocate costs by team or project
* **Adoption monitoring**: Identify which teams and users are getting the most value from Claude Code
* **ROI justification**: Provide concrete metrics to justify and expand Claude Code adoption internally

## Frequently asked questions

### How fresh is the analytics data?

Claude Code analytics data typically appears within 1 hour of user activity completion. To ensure consistent pagination results, only data older than 1 hour is included in responses.

### Can I get real-time metrics?

No, this API provides daily aggregated metrics only. For real-time monitoring, consider using the [OpenTelemetry integration](/en/docs/claude-code/monitoring-usage).

### How are users identified in the data?

Users are identified through the `actor` field in two ways:

* **`user_actor`**: Contains `email_address` for users who authenticate via OAuth (most common)
* **`api_actor`**: Contains `api_key_name` for users who authenticate via API key

The `customer_type` field indicates whether the usage is from `api` customers (API PAYG) or `subscription` customers (Pro/Team plans).

### What's the data retention period?

Historical Claude Code analytics data is retained and accessible through the API. There is no specified deletion period for this data.

### Which Claude Code deployments are supported?

This API only tracks Claude Code usage on the Claude API (1st party). Usage on Amazon Bedrock, Google Vertex AI, or other third-party platforms is not included.

### What does it cost to use this API?

The Claude Code Analytics API is free to use for all organizations with access to the Admin API.

### How do I calculate tool acceptance rates?

Tool acceptance rate = `accepted / (accepted + rejected)` for each tool type. For example, if the edit tool shows 45 accepted and 5 rejected, the acceptance rate is 90%.

### What time zone is used for the date parameter?

All dates are in UTC. The `starting_at` parameter should be in YYYY-MM-DD format and represents UTC midnight for that day.

## See also

The Claude Code Analytics API helps you understand and optimize your team's development workflow. Learn more about related features:

* [Admin API overview](/en/api/administration-api)
* [Admin API reference](/en/api/admin-api)
* [Claude Code Analytics dashboard](https://console.anthropic.com/claude-code)
* [Usage and Cost API](/en/api/usage-cost-api) - Track API usage across all Anthropic services
* [Identity and access management](/en/docs/claude-code/iam)
* [Monitoring usage with OpenTelemetry](/en/docs/claude-code/monitoring-usage) for custom metrics and alerting
