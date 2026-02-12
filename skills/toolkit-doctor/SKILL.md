# toolkit-doctor

Diagnose and repair the thesqrldev-claudecode-toolkit installation.

## Instructions

Run the following checks:

### 1. Installation check
- Verify `${CLAUDE_PLUGIN_ROOT}` exists and is a git repository
- Check remote URL matches `quantsquirrel/thesqrldev-claudecode-toolkit`

### 2. Plugin integrity
For each plugin in `config/registry.json`:
- Directory exists under `plugins/`
- `.git-sha` file present
- `.claude-plugin/` directory or `plugin.json` present in expected location

### 3. Hook integrity
- `hooks/hooks.json` exists and is valid JSON
- `hooks/update-checker.mjs` exists

### 4. Skill integrity
- All skill directories under `skills/` have a `SKILL.md`

### Recovery suggestions
For each failed check, provide a fix command:
- Missing plugin: "Run the sync workflow: `gh workflow run sync-plugins.yml -R quantsquirrel/thesqrldev-claudecode-toolkit`"
- Missing git-sha: "Plugin not yet synced by CI"
- Broken hooks: "Re-install: `claude plugin install gh:quantsquirrel/thesqrldev-claudecode-toolkit`"

## Trigger
- User says "toolkit doctor", "check toolkit", "toolkit health"
- `/toolkit:doctor`
