# BMad-Archon Integration Fix

## Problem Identified
The CLAUDE.md file was overwritten with "ARCHON-FIRST RULE" that made Archon task management primary, completely bypassing BMad method workflow.

## Root Cause
- CLAUDE.md contained "ARCHON-FIRST RULE" that overrode all other instructions
- This made every interaction start with Archon find_tasks/manage_task calls
- Completely replaced BMad story-driven workflow with generic task management

## Correct Integration
BMad Method should be **primary** with Archon as **complementary**:

### BMad Primary Workflow:
- Use `/BMad:sm` for story creation via `create-next-story.md` task
- Use `/BMad:dev` for story implementation 
- Use `/BMad:qa` for quality validation
- Stories stored in `docs/stories/` following BMad structure

### Archon Complementary:
- RAG knowledge search: `rag_search_knowledge_base()`, `rag_search_code_examples()`
- Optional project tracking: `find_tasks()`, `manage_task()` for high-level coordination
- NOT primary task management - should not replace BMad stories

## Key Files Fixed:
- `/CLAUDE.md` - Restored proper BMad method with Archon as complementary
- BMad agents (`.bmad-core/agents/`) were correctly configured with `mcp_tools_context`

## Prevention:
Never replace BMad workflow with pure Archon task management. Archon should enhance BMad, not replace it.

## Correct Usage Pattern:
1. Use `/BMad:sm` to create stories (primary workflow)
2. Use Archon RAG for research during implementation
3. Optionally create Archon tasks for project coordination
4. Always follow BMad story-driven development process