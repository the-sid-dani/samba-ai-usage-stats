# BMad Method Project Configuration

This project uses the BMad Method for structured development with Archon MCP integration for enhanced project tracking.

## BMad Method Overview

BMad follows a structured workflow:
1. **Planning Phase**: PM creates PRD, Architect designs system
2. **Story Creation**: SM drafts stories from epics and architecture
3. **Development**: Dev implements stories with proper testing
4. **Quality Assurance**: QA reviews and validates implementation

## Agent Usage

Use BMad agents via slash commands:
- `/BMad:pm` - Product Manager (PRDs, requirements)
- `/BMad:architect` - System Architect (architecture, design)
- `/BMad:sm` - Scrum Master (story creation, workflow)
- `/BMad:dev` - Developer (implementation, coding)
- `/BMad:qa` - Quality Assurance (testing, review)
- `/BMad:bmad-master` - Universal executor (any BMad task)

## File Structure

```
docs/
├── prd.md                  # Product Requirements Document
├── architecture.md         # System Architecture
├── prd/                    # Sharded PRD sections
├── architecture/           # Sharded architecture docs
├── stories/                # User stories for development
└── qa/                     # QA assessments and gates
```

## Archon Integration (Complementary)

Archon MCP server provides additional project tracking capabilities:

### When to Use Archon
- **Knowledge Research**: Use `rag_search_knowledge_base()` for technical research
- **Project Tracking**: Optional high-level project coordination
- **Code Examples**: Use `rag_search_code_examples()` for implementation patterns

### Archon RAG Workflow
```bash
# Research before implementation
rag_get_available_sources()                    # List available documentation
rag_search_knowledge_base(query="auth JWT")    # Search specific topics
rag_search_code_examples(query="React hooks")  # Find code patterns
```

### Story-Task Coordination
- **Primary**: BMad stories in `docs/stories/`
- **Secondary**: Optional Archon tasks for project coordination
- **Integration**: Stories provide dev context, Archon provides project visibility

## Development Workflow

1. **Start with BMad**: Use `/BMad:sm` to create or review stories
2. **Research**: Use Archon RAG tools for technical research if needed
3. **Implement**: Use `/BMad:dev` for story implementation
4. **Review**: Use `/BMad:qa` for quality validation
5. **Track**: Optionally update Archon tasks for project visibility

## Key Principles

- **BMad Method Primary**: Follow BMad workflows and agent responsibilities
- **Archon Complementary**: Use for research and optional project tracking
- **Story-Driven**: Work from BMad stories, not generic tasks
- **Agent Specialization**: Use appropriate BMad agents for their expertise