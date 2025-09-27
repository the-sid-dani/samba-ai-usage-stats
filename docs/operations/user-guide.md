# AI Usage Analytics - User Guide

## 🎯 Purpose
Step-by-step guide for finance team members to navigate dashboards, generate reports, and interpret AI usage analytics.

## 👤 Intended Users
- Finance Team Members
- Team Leads
- Department Managers

---

## 📊 Dashboard Overview

### Executive Dashboard
**Purpose**: High-level KPIs and cost trends for executive reporting

**Key Metrics**:
- Total monthly AI costs
- Cost per user
- Month-over-month growth
- Platform cost distribution
- Annual run rate forecasts

**Best For**: Monthly executive reports, budget planning

### Cost Allocation Dashboard
**Purpose**: Detailed cost breakdowns by user, team, and project

**Key Metrics**:
- Cost per line of code accepted
- User productivity rankings
- Team efficiency comparisons
- ROI analysis

**Best For**: Department budget allocation, performance reviews

### Productivity Analytics Dashboard
**Purpose**: Engineering productivity insights and trends

**Key Metrics**:
- Code acceptance rates
- Lines of code trends
- User activity levels
- Platform adoption

**Best For**: Engineering management, productivity analysis

---

## 🖱️ Dashboard Navigation

### Accessing Dashboards

1. **Login to Looker Studio**
   - Go to [datastudio.google.com](https://datastudio.google.com)
   - Use your company Google account
   - Navigate to "AI Usage Analytics" folder

2. **Dashboard Selection**
   - **Executive Summary**: For monthly finance reviews
   - **Cost Allocation**: For detailed cost analysis
   - **Productivity Metrics**: For engineering insights

### Using Filters

#### Date Range Filter
- **Default**: Last 6 months
- **Recommended**:
  - Monthly reviews: Last 3 months
  - Quarterly reviews: Last 12 months
  - Trend analysis: Full available history

#### Platform Filter
- **Anthropic**: Claude API usage and costs
- **Cursor**: Code completion tool usage
- **All Platforms**: Combined view (recommended for totals)

#### User/Team Filter
- Filter by email domain for department views
- Use individual emails for user-specific analysis
- Leave blank for organization-wide view

### Reading Charts and Tables

#### Cost Trend Charts
- **Green trend**: Cost growth within expected range (<20%)
- **Yellow trend**: Moderate cost increase (20-50%)
- **Red trend**: High cost increase (>50%) - requires investigation

#### Productivity Metrics
- **Acceptance Rate**: Percentage of suggested code accepted
  - >80%: Excellent
  - 60-80%: Good
  - 40-60%: Average
  - <40%: Needs attention

#### ROI Indicators
- **Cost per Line Accepted**: Lower is better
  - <$0.15: Excellent ROI
  - $0.15-$0.30: Good ROI
  - $0.30-$0.50: Acceptable ROI
  - >$0.50: Poor ROI

---

## 📋 Common Report Generation

### Monthly Finance Report

1. **Open Executive Dashboard**
2. **Set Date Filter**: Previous complete month
3. **Export Data**:
   - Click "Export" → "Google Sheets"
   - Name: "AI Usage Report - [Month Year]"
   - Save to "Finance Reports" folder

4. **Key Metrics to Include**:
   - Total monthly cost
   - Cost by platform
   - Top 10 users by cost
   - Month-over-month growth
   - Annual run rate projection

### Team Performance Review

1. **Open Cost Allocation Dashboard**
2. **Filter by Team/Department**:
   - Use email domain filter (@engineering.company.com)
3. **Review Metrics**:
   - Team total costs
   - Individual user productivity
   - Efficiency rankings
   - ROI comparisons

4. **Generate Summary**:
   - Export top/bottom performers
   - Include productivity trends
   - Note efficiency improvements

### Budget Planning Support

1. **Open Executive Dashboard**
2. **Set Date Range**: Last 12 months
3. **Analyze Trends**:
   - Identify seasonal patterns
   - Calculate growth rates
   - Project future costs

4. **Export Forecast Data**:
   - Annual run rate
   - Quarterly projections
   - Platform cost distribution

---

## 🔍 Data Interpretation Guide

### Understanding Cost Metrics

#### Platform Costs
- **Anthropic (Claude API)**: Pay-per-token usage
  - Typical range: $50-$300 per active user/month
  - Driven by: API calls, input/output token volume

- **Cursor (Code Completion)**: Subscription + usage
  - Typical range: $20-$100 per active user/month
  - Driven by: Code suggestions, acceptance rates

#### User Cost Patterns
- **Power Users**: >$200/month, high productivity
- **Regular Users**: $50-$200/month, moderate usage
- **Occasional Users**: <$50/month, sporadic usage

### Understanding Productivity Metrics

#### Acceptance Rates
- **80%+**: User finds AI suggestions highly valuable
- **60-80%**: Good adoption, minor optimization opportunities
- **40-60%**: Average usage, training may help
- **<40%**: Poor adoption, investigate user experience

#### Lines of Code Trends
- **Increasing**: Growing AI adoption and productivity
- **Flat**: Stable usage patterns
- **Decreasing**: May indicate tool issues or user churn

### ROI Analysis

#### Cost per Line Accepted
**Calculation**: Total platform cost ÷ Total lines accepted

**Benchmarks**:
- **Excellent** (<$0.15): AI is highly cost-effective
- **Good** ($0.15-$0.30): Positive ROI, good value
- **Acceptable** ($0.30-$0.50): Break-even, monitor trends
- **Poor** (>$0.50): Re-evaluate usage patterns

---

## ⚠️ Common Issues and Solutions

### Dashboard Issues

#### "No Data Available"
**Causes**:
- Date range outside available data
- User permissions issue
- Data pipeline failure

**Solutions**:
1. Adjust date range to last 30 days
2. Contact admin for permissions
3. Check pipeline status in runbook

#### "Dashboard Loading Slowly"
**Causes**:
- Large date range selected
- Complex filters applied
- BigQuery performance issues

**Solutions**:
1. Reduce date range to 3 months
2. Remove unused filters
3. Contact Data Engineering if persistent

### Data Quality Issues

#### "Missing Users in Reports"
**Causes**:
- New users not in API key mapping
- Email format mismatches
- API key not properly attributed

**Solutions**:
1. Add user to Google Sheets mapping
2. Standardize email formats
3. Verify API key ownership

#### "Unexpected Cost Spikes"
**Causes**:
- New high-usage users
- API quota changes
- Data processing errors

**Solutions**:
1. Review Cost Allocation Dashboard
2. Identify top cost contributors
3. Investigate usage patterns

---

## 📞 Getting Help

### Self-Service Resources
1. **This User Guide** - Navigation and interpretation
2. **Dashboard Help**: Click "?" icon in Looker Studio
3. **FAQ**: [Internal Wiki Link]

### Contact Support

#### For Dashboard Questions
- **Slack**: #ai-usage-analytics
- **Email**: data-engineering@company.com
- **Response Time**: 4 hours during business hours

#### For Cost/Budget Questions
- **Slack**: #finance-support
- **Email**: finance@company.com
- **Response Time**: Same day

#### For Technical Issues
- **Slack**: #platform-support
- **Email**: platform-team@company.com
- **Response Time**: 2 hours for critical issues

### Training Resources
- **Monthly Office Hours**: First Tuesday, 2 PM
- **Video Tutorials**: [Internal Training Portal]
- **Best Practices Guide**: [Link to internal docs]

---

## 🎓 Tips for Effective Usage

### Dashboard Best Practices
1. **Start Broad**: Use Executive Dashboard for overview
2. **Drill Down**: Use filters to investigate specific patterns
3. **Compare Periods**: Use month-over-month comparisons
4. **Export Regularly**: Save monthly snapshots for historical reference

### Data Analysis Tips
1. **Look for Patterns**: Seasonal trends, user behavior changes
2. **Cross-Reference**: Compare cost and productivity metrics
3. **Focus on Outliers**: Investigate unusually high/low performers
4. **Track Trends**: Monitor month-over-month changes

### Reporting Recommendations
1. **Executive Reports**: Focus on totals and trends
2. **Department Reports**: Include user-level details
3. **Budget Planning**: Use 12-month rolling averages
4. **Performance Reviews**: Include efficiency rankings