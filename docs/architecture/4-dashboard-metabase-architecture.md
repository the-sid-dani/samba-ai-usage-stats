# 📊 **4-DASHBOARD METABASE ARCHITECTURE**

## **Dashboard Ecosystem Overview**

Our Metabase architecture supports **4 specialized dashboards** optimized for different stakeholder groups:

### **Dashboard 1: Engineering Productivity** 👨‍💻
**Target Users:** Engineering Managers, Team Leads, Senior Developers
**Data Sources:** `vw_ai_coding_productivity` (Cursor + Claude Code)
**Core Metrics:**
- Lines of code assisted by AI tools
- Acceptance rates and coding efficiency
- Team productivity rankings
- Tool effectiveness comparison (Cursor vs Claude Code)
- Individual developer performance trends

**Key Visualizations:**
- Daily/weekly lines accepted trends
- Team productivity heatmap
- Acceptance rate distribution
- Cost per line efficiency analysis

### **Dashboard 2: API Consumption** ⚙️
**Target Users:** Technical Architects, DevOps Teams, Cost Engineers
**Data Sources:** `vw_api_consumption` (Claude API + Cursor API)
**Core Metrics:**
- Token consumption and API request volumes
- Cost per token/request optimization
- API usage patterns and efficiency
- Infrastructure automation effectiveness

**Key Visualizations:**
- Token usage trends over time
- Cost per 1K tokens analysis
- API efficiency ratios
- Usage pattern identification

### **Dashboard 3: Knowledge Workers Productivity** 💼
**Target Users:** Product Managers, Analysts, Content Teams, Researchers
**Data Sources:** `vw_ai_assistant_productivity` (claude.ai + Gemini)
**Core Metrics:**
- Conversations and projects created
- Research and analysis efficiency
- File analysis productivity
- Knowledge work ROI measurement

**Key Visualizations:**
- Daily conversation trends
- Project completion rates
- Research efficiency scores
- Knowledge work cost analysis

### **Dashboard 4: Executive Overview** 👔
**Target Users:** C-Suite, Finance Leadership, Department Heads
**Data Sources:** `vw_executive_total_investment` (Cross-category)
**Core Metrics:**
- Total AI investment across all categories
- ROI comparison between AI categories
- Budget vs actual spending
- Strategic AI adoption insights

**Key Visualizations:**
- Total AI spend trending
- ROI comparison by category
- User AI investment profiles
- Budget variance analysis

## **Dashboard Performance Architecture**

### **Pre-Aggregated Summary Tables for Metabase:**
```sql
-- Monthly summaries for fast dashboard performance
CREATE TABLE mb_monthly_summary (
  summary_month DATE,
  user_email STRING,
  department STRING,

  -- Category 1: AI Coding (Cursor + Claude Code)
  total_coding_lines INT64,
  total_coding_cost FLOAT64,
  coding_efficiency_score FLOAT64,

  -- Category 2: API Usage (Claude API + Cursor API)
  total_api_tokens INT64,
  total_api_cost FLOAT64,
  api_efficiency_score FLOAT64,

  -- Category 3: AI Assistants (claude.ai + Gemini)
  total_conversations INT64,
  total_assistant_cost FLOAT64,
  assistant_efficiency_score FLOAT64,

  -- Executive metrics
  total_ai_investment FLOAT64,
  user_ai_profile STRING
);

-- Real-time current month view for live metrics
CREATE VIEW mb_current_month_live AS (
  SELECT * FROM daily_facts
  WHERE DATE_TRUNC(activity_date, MONTH) = DATE_TRUNC(CURRENT_DATE(), MONTH)
);
```

---
