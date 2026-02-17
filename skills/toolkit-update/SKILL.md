# toolkit-update

Update the thesqrldev-claudecode-toolkit to the latest version.

## Instructions

The plugin cache (`~/.claude/plugins/cache/`) does NOT contain `.git`, so `git pull` cannot be used.
Use the approach below to update from within a session.

### Step 1: Clone latest to a temp directory

```bash
REPO_URL="https://github.com/quantsquirrel/thesqrldev-claudecode-toolkit.git"
TMPDIR=$(mktemp -d)
git clone --depth 1 "$REPO_URL" "$TMPDIR/toolkit"
```

### Step 2: Find and sync to the plugin cache

```bash
CACHE_DIR=$(find "$HOME/.claude/plugins/cache/thesqrldev-toolkit" -name "plugin.json" -path "*/.claude-plugin/*" -exec dirname {} \; 2>/dev/null | head -1 | xargs dirname)
if [ -z "$CACHE_DIR" ]; then
  echo "ERROR: Plugin cache not found. Is the plugin installed?"
else
  rsync -av --delete --exclude='.git' --exclude='.omc' "$TMPDIR/toolkit/" "$CACHE_DIR/"
  echo "Synced to: $CACHE_DIR"
fi
```

### Step 3: Show what changed and clean up

```bash
cd "$TMPDIR/toolkit" && git log --oneline -5
rm -rf "$TMPDIR"
```

### Step 4: Report

1. Whether the update succeeded
2. Which recent commits were included (`git log` output from Step 3)
3. **Always suggest restarting the session** — hooks and skills are loaded at session start

### Alternative: CLI update (outside session)

If the user is NOT inside an active Claude Code session, they can use the built-in command:

```bash
claude plugin update thesqrldev-toolkit
```

This is the official method but cannot run from within an active session.

## Trigger
- User says "toolkit update", "update toolkit", "update plugins"
- `/toolkit:update`
