<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-11T00:00:00Z | Updated: 2026-02-11T00:00:00Z -->

# .claude-plugin/

## Purpose

Plugin marketplace metadata directory. Contains plugin registration, versioning, and marketplace integration files. Defines how the Blueprint plugin appears in Claude Code's marketplace and establishes installation/discovery metadata.

## Key Files

| File | Description |
|------|-------------|
| `marketplace.json` | Anthropic marketplace schema compliance file; defines plugin display name, description, category, tags, and owner metadata |
| `plugin.json` | Plugin metadata: name, version, description, author; referenced by parent `plugin.json` |

## Subdirectories

None

## For AI Agents

### Working In This Directory

- **Schema compliance**: Both JSON files must conform to Anthropic's plugin schemas
- **Versioning**: Must match version in root `package.json` and `plugin.json`
- **Marketplace sync**: Changes to `marketplace.json` require re-publishing to marketplace
- **No code**: This directory contains configuration only - no JavaScript/TypeScript files
- **File format**: Standard JSON (no comments, UTF-8 encoding)
- **Read-only for runtime**: These files are read at plugin load time; changes require plugin reload

### Testing Requirements

- Validate JSON syntax: `node -e "JSON.parse(require('fs').readFileSync('./marketplace.json'))"`
- Verify schema compliance against Anthropic's published marketplace schema
- Confirm version consistency across `marketplace.json`, `plugin.json`, root `package.json`
- Test plugin discovery in Claude Code after schema changes

### Common Patterns

- **Marketplace schema**: Schema URL defined in `marketplace.json` root; always use current version
- **Plugin definition**: Single plugin entry in `marketplace.json["plugins"]` array
- **Metadata sync**: Keep author, version, description synchronized across both files and root manifests
- **Category tags**: Use lowercase, hyphenated tags for consistency (e.g., `pdca`, `gap-analysis`)

## Dependencies

### Internal

- Root `plugin.json` - must reference these files
- Root `package.json` - version field must match
- Root `AGENTS.md` - architectural context

### External

- Anthropic marketplace schema (published via JSON schema URL)
- Claude Code plugin loader (automatic discovery at session start)

## Marketplace Integration

**Workflow:**
1. User searches Claude Code marketplace for "blueprint"
2. Marketplace returns plugin entry from `marketplace.json`
3. User clicks "Install"
4. Claude Code clones repo and runs plugin setup
5. `plugin.json` metadata loaded for plugin registration

**Fields (marketplace.json):**
- `name`: Plugin name (top level)
- `plugins[].name`: Display name in marketplace
- `plugins[].description`: Short description (1-2 sentences)
- `plugins[].category`: Categorization (`productivity`, `development`, etc.)
- `plugins[].tags`: Search keywords (array of lowercase strings)
- `plugins[].homepage`: GitHub URL
- `plugins[].author`: Author metadata
- `plugins[].version`: Version string (must match root `package.json`)

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
