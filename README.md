# thesqrldev-claudecode-toolkit

A curated Claude Code plugin toolkit by [quantsquirrel](https://github.com/quantsquirrel) — four plugins bundled for easy team onboarding.

## Plugins

| Plugin | Description | Repo |
|--------|-------------|------|
| **handoff** | Session context handoff — save before autocompact, restore with clipboard | [claude-handoff-baton](https://github.com/quantsquirrel/claude-handoff-baton) |
| **synod** | Multi-agent deliberation with structured debate (Claude + Gemini + OpenAI) | [claude-synod-debate](https://github.com/quantsquirrel/claude-synod-debate) |
| **blueprint** | PDCA cycle, Gap Analysis, Dev Pipeline for systematic development | [claude-blueprint-helix](https://github.com/quantsquirrel/claude-blueprint-helix) |
| **forge** | TDD-powered automatic skill evolution with statistical validation | [claude-forge-smith](https://github.com/quantsquirrel/claude-forge-smith) |

## Install

```bash
claude plugin install gh:quantsquirrel/thesqrldev-claudecode-toolkit
```

All four plugins + management skills are installed at once.

## Management Skills

| Skill | Description |
|-------|-------------|
| `/toolkit:update` | Pull latest synced plugins |
| `/toolkit:list` | Show plugin status table |
| `/toolkit:doctor` | Diagnose installation health |

## How It Works

Plugins are **not** git submodules. A daily CI workflow ([sync-plugins.yml](.github/workflows/sync-plugins.yml)) mirrors each upstream repo into `plugins/`. This means:

- **Adding a plugin**: Add an entry to `config/registry.json`, CI does the rest
- **Updating**: Push to any upstream repo → CI syncs within 24h (or trigger manually)
- **No local clones needed**: Everything is managed via GitHub Actions

```
You push to claude-handoff-baton
  → CI syncs to plugins/handoff/
    → Team member starts session → update-checker notifies
      → /toolkit:update pulls latest
```

## Manual Sync

Trigger the workflow manually:

```bash
gh workflow run sync-plugins.yml -R quantsquirrel/thesqrldev-claudecode-toolkit
```

## License

[MIT](LICENSE)
