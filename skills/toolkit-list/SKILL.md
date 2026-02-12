# toolkit-list

List all plugins in the thesqrldev-claudecode-toolkit with their status.

## Instructions

Read `${CLAUDE_PLUGIN_ROOT}/config/registry.json` and for each plugin:
1. Check if `${CLAUDE_PLUGIN_ROOT}/plugins/{name}/.git-sha` exists
2. Read the SHA if available
3. Check if the plugin directory exists and has content

Display a table:

| Plugin | Version | SHA | Status |
|--------|---------|-----|--------|
| handoff | 2.3.0 | abc1234 | synced |
| synod | 3.0.0 | def5678 | synced |
| blueprint | 1.0.0 | ghi9012 | synced |
| forge | 1.0.0 | jkl3456 | synced |

Get version from each plugin's `.claude-plugin/plugin.json` or `.claude-plugin/marketplace.json`.

Status values: `synced` (has .git-sha), `pending` (directory exists but no SHA), `missing` (no directory).

## Trigger
- User says "list plugins", "toolkit list", "show plugins"
- `/toolkit:list`
