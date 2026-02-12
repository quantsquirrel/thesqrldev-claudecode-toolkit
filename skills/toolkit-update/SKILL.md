# toolkit-update

Update the thesqrldev-claudecode-toolkit to the latest version by pulling from remote.

## Instructions

Run `git pull` in the toolkit plugin directory to fetch the latest synced plugins.

```bash
cd "${CLAUDE_PLUGIN_ROOT}" && git pull --ff-only
```

After pulling, report:
1. Whether any changes were pulled
2. Which plugins were updated (check `git log --oneline -5`)
3. Suggest restarting the session if hooks or skills changed

## Trigger
- User says "toolkit update", "update toolkit", "update plugins"
- `/toolkit:update`
