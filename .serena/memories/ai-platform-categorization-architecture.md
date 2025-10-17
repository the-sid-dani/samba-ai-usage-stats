# AI Platform Categorization Architecture

## Platform Categories for Data Model Design

### 1. AI Coding Agents (Lines of Code Metrics)
**Purpose**: Engineering productivity tracking via code output
**Platforms**: 
- **Cursor**: Lines suggested/accepted, coding assistance
- **Claude Code**: Lines added/removed, IDE integration, tool acceptance rates

**Key Metrics**: 
- Lines of code added/accepted
- Acceptance rates
- Coding productivity scores
- Development velocity

**Join Logic**: `cursor + claude_code` for engineering productivity dashboards

### 2. API Usage (Token-Based Metrics)  
**Purpose**: Direct API consumption and cost tracking
**Platforms**:
- **Claude API**: Token usage (input/output), API requests, direct API costs
- **Cursor API**: Extra requests beyond subscription limits, API-based usage

**Key Metrics**:
- Tokens in/out
- API request counts  
- Cost per token/request
- API efficiency ratios

**Join Logic**: `claude_api + cursor_api` for API consumption analytics

### 3. AI Assistants (Conversation/Interaction Metrics)
**Purpose**: Knowledge worker productivity and general AI assistance
**Platforms**:
- **claude.ai**: Web conversations, projects, file analysis
- **Google Gemini**: General AI assistance (future)
- **ChatGPT**: General AI assistance (future)

**Key Metrics**:
- Conversations created
- Projects completed
- Files analyzed
- Knowledge work efficiency

**Join Logic**: Separate category - conversation-based productivity tracking

## Critical Design Principle
Each category has fundamentally different metrics and business purposes:
- **Coding Agents**: Output = lines of code
- **API Usage**: Output = tokens/requests  
- **AI Assistants**: Output = conversations/projects

Do NOT mix categories in primary analytics - they measure different types of productivity.