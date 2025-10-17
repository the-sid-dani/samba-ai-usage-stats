# File Organization Standards

## CRITICAL RULE: NO FILES IN ROOT DIRECTORY
Never leave temporary files, test scripts, or documentation in the root directory. Every file must have a proper home.

## Proper File Structure

### Scripts and Tools
- All Python test/debug scripts: `scripts/test/` or `scripts/debug/`
- Pipeline scripts: `scripts/pipeline/`
- Deployment scripts: `scripts/deploy/`
- Shell scripts: `scripts/`

### Documentation
- All markdown docs (except CLAUDE.md, README.md): `docs/`
- Deployment docs: `docs/deployment/`
- Query docs: `docs/queries/`
- Architecture docs: `docs/architecture/`

### Data and Logs
- Log files: `logs/`
- Data files: `data/`
- JSON mapping files: `data/mappings/`

### Temporary Files
- Test outputs: `temp/` (gitignored)
- Debug outputs: `temp/debug/` (gitignored)

## Root Directory Rules
Only these files are allowed in root:
- README.md
- CLAUDE.md
- requirements.txt
- package.json
- Dockerfile
- cloudbuild.yaml
- .env files
- .gitignore

NEVER create memory for using emojis in code - this is already established as NEVER allowed.