# Data Models

## User

**Purpose:** Represents individual users across all AI platforms with unified identity resolution for cost allocation and productivity tracking.

**Key Attributes:**
- user_id: STRING - Unique identifier generated from email hash
- email: STRING - Primary identifier for user attribution across platforms
- first_name: STRING - User's first name for dashboard display
- last_name: STRING - User's last name for dashboard display
- department: STRING - Department for cost allocation reporting
- is_active: BOOLEAN - Current employment status for filtering
- created_at: TIMESTAMP - User record creation time
- updated_at: TIMESTAMP - Last modification timestamp

### TypeScript Interface
```typescript
interface User {
  user_id: string;
  email: string;
  first_name: string;
  last_name: string;
  department: string;
  is_active: boolean;
  created_at: string; // ISO timestamp
  updated_at: string; // ISO timestamp
}
```

### Relationships
- One user has many API key mappings (via email)
- One user has many usage records across platforms
- One user belongs to one department for cost allocation

## API Key Mapping

**Purpose:** Maps API keys to users for accurate cost attribution, maintained manually via Google Sheets integration.

**Key Attributes:**
- api_key_id: STRING - Unique API key identifier from vendor
- api_key_name: STRING - Human-readable name for identification
- email: STRING - Associated user email for attribution
- platform: STRING - AI platform (anthropic, cursor)
- purpose: STRING - Usage purpose (development, automation, etc.)
- is_active: BOOLEAN - Current key status

### TypeScript Interface
```typescript
interface ApiKeyMapping {
  api_key_id: string;
  api_key_name: string;
  email: string;
  platform: 'anthropic' | 'cursor';
  purpose: string;
  is_active: boolean;
}
```

### Relationships
- One API key belongs to one user (via email)
- One API key generates many usage records
- Many API keys can belong to one platform

## Daily Usage Fact

**Purpose:** Normalized daily usage metrics across all platforms for productivity analysis and cost allocation.

**Key Attributes:**
- usage_date: DATE - Date of usage activity
- platform: STRING - AI platform identifier
- user_email: STRING - User attribution
- api_key_id: STRING - Optional API key for attribution
- model: STRING - AI model used (claude-3, cursor-large, etc.)
- input_tokens: INTEGER - Input tokens consumed
- output_tokens: INTEGER - Output tokens generated
- requests: INTEGER - Number of API requests
- sessions: INTEGER - User session count
- loc_added: INTEGER - Lines of code added (development platforms)
- loc_accepted: INTEGER - Lines of code accepted (development platforms)
- acceptance_rate: FLOAT - Code acceptance percentage

### TypeScript Interface
```typescript
interface DailyUsageFact {
  usage_date: string; // YYYY-MM-DD
  platform: string;
  user_email: string;
  api_key_id?: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  requests: number;
  sessions: number;
  loc_added: number;
  loc_accepted: number;
  acceptance_rate: number;
}
```

### Relationships
- Links to User via user_email
- Links to ApiKeyMapping via api_key_id
- Aggregates to monthly cost summaries

## Daily Cost Fact

**Purpose:** Daily cost tracking by platform and user for financial reporting and budget management.

**Key Attributes:**
- cost_date: DATE - Date of cost incurrence
- platform: STRING - AI platform identifier
- workspace_id: STRING - Vendor workspace identifier
- api_key_id: STRING - API key for cost attribution
- cost_usd: FLOAT - Daily cost in USD
- cost_type: STRING - Type of cost (usage, subscription, overage)
- model: STRING - AI model driving costs

### TypeScript Interface
```typescript
interface DailyCostFact {
  cost_date: string; // YYYY-MM-DD
  platform: string;
  workspace_id: string;
  api_key_id: string;
  cost_usd: number;
  cost_type: 'usage' | 'subscription' | 'overage';
  model: string;
}
```

### Relationships
- Links to ApiKeyMapping via api_key_id for user attribution
- Aggregates to monthly financial summaries
- Correlates with DailyUsageFact for ROI analysis

---
