#!/bin/bash
#
# Auto-Handoff Hook Installer
#
# Installs the auto-handoff hook to Claude Code settings.
# Run: bash install.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETTINGS_FILE="$HOME/.claude/settings.json"

echo "📋 Auto-Handoff Hook Installer"
echo "=============================="
echo ""

# Check if settings file exists
if [ ! -f "$SETTINGS_FILE" ]; then
    echo "Creating $SETTINGS_FILE..."
    mkdir -p "$HOME/.claude"
    echo '{}' > "$SETTINGS_FILE"
fi

# Check if hooks are already configured
if grep -q "auto-handoff.mjs" "$SETTINGS_FILE" 2>/dev/null && \
   grep -q "task-size-estimator.mjs" "$SETTINGS_FILE" 2>/dev/null && \
   grep -q "pre-compact.mjs" "$SETTINGS_FILE" 2>/dev/null && \
   grep -q "session-restore.mjs" "$SETTINGS_FILE" 2>/dev/null; then
    echo "✅ Auto-handoff hooks are already installed!"
    echo ""
    echo "Installed hooks:"
    echo "  • PrePromptSubmit: task-size-estimator.mjs (task size detection)"
    echo "  • PostToolUse: auto-handoff.mjs (context monitoring)"
    echo "  • PreCompact: pre-compact.mjs (metadata snapshot)"
    echo "  • SessionStart: session-restore.mjs (context restoration)"
    echo ""
    echo "To uninstall, remove the hook entries from:"
    echo "  $SETTINGS_FILE"
    exit 0
fi

# Backup existing settings
cp "$SETTINGS_FILE" "$SETTINGS_FILE.backup"
echo "📁 Backed up settings to $SETTINGS_FILE.backup"

# Create the hook configurations
AUTO_HANDOFF_PATH="$SCRIPT_DIR/auto-handoff.mjs"
TASK_SIZE_PATH="$SCRIPT_DIR/task-size-estimator.mjs"
PRE_COMPACT_PATH="$SCRIPT_DIR/pre-compact.mjs"
SESSION_RESTORE_PATH="$SCRIPT_DIR/session-restore.mjs"

# Use Node.js to safely merge the hook configuration
node -e "
const fs = require('fs');
const settingsFile = '$SETTINGS_FILE';
const autoHandoffPath = '$AUTO_HANDOFF_PATH';
const taskSizePath = '$TASK_SIZE_PATH';
const preCompactPath = '$PRE_COMPACT_PATH';
const sessionRestorePath = '$SESSION_RESTORE_PATH';

// Read existing settings
let settings = {};
try {
    settings = JSON.parse(fs.readFileSync(settingsFile, 'utf8'));
} catch (e) {
    settings = {};
}

// Ensure hooks structure exists
if (!settings.hooks) {
    settings.hooks = {};
}
if (!settings.hooks.PostToolUse) {
    settings.hooks.PostToolUse = [];
}
if (!settings.hooks.PrePromptSubmit) {
    settings.hooks.PrePromptSubmit = [];
}
if (!settings.hooks.PreCompact) {
    settings.hooks.PreCompact = [];
}
if (!settings.hooks.SessionStart) {
    settings.hooks.SessionStart = [];
}

// Add task-size-estimator hook (PrePromptSubmit)
const taskSizeHook = {
    hooks: [{
        type: 'command',
        command: 'node ' + taskSizePath
    }]
};

const taskSizeExists = settings.hooks.PrePromptSubmit.some(h =>
    h.hooks && h.hooks.some(hh =>
        hh.command && hh.command.includes('task-size-estimator.mjs')
    )
);

if (!taskSizeExists) {
    settings.hooks.PrePromptSubmit.push(taskSizeHook);
    console.log('✅ PrePromptSubmit hook (task-size-estimator) added!');
} else {
    console.log('⚠️ PrePromptSubmit hook already configured.');
}

// Add auto-handoff hook (PostToolUse)
const autoHandoffHook = {
    matcher: 'Read|Grep|Glob|Bash|WebFetch',
    hooks: [{
        type: 'command',
        command: 'node ' + autoHandoffPath
    }]
};

const autoHandoffExists = settings.hooks.PostToolUse.some(h =>
    h.hooks && h.hooks.some(hh =>
        hh.command && hh.command.includes('auto-handoff.mjs')
    )
);

if (!autoHandoffExists) {
    settings.hooks.PostToolUse.push(autoHandoffHook);
    console.log('✅ PostToolUse hook (auto-handoff) added!');
} else {
    console.log('⚠️ PostToolUse hook already configured.');
}

// Add pre-compact hook (PreCompact)
const preCompactHook = {
    hooks: [{
        type: 'command',
        command: 'node ' + preCompactPath
    }]
};

const preCompactExists = settings.hooks.PreCompact.some(h =>
    h.hooks && h.hooks.some(hh =>
        hh.command && hh.command.includes('pre-compact.mjs')
    )
);

if (!preCompactExists) {
    settings.hooks.PreCompact.push(preCompactHook);
    console.log('✅ PreCompact hook (pre-compact) added!');
} else {
    console.log('⚠️ PreCompact hook already configured.');
}

// Add session-restore hook (SessionStart)
const sessionRestoreHook = {
    hooks: [{
        type: 'command',
        command: 'node ' + sessionRestorePath
    }]
};

const sessionRestoreExists = settings.hooks.SessionStart.some(h =>
    h.hooks && h.hooks.some(hh =>
        hh.command && hh.command.includes('session-restore.mjs')
    )
);

if (!sessionRestoreExists) {
    settings.hooks.SessionStart.push(sessionRestoreHook);
    console.log('✅ SessionStart hook (session-restore) added!');
} else {
    console.log('⚠️ SessionStart hook already configured.');
}

// Save settings
fs.writeFileSync(settingsFile, JSON.stringify(settings, null, 2));
"

echo ""
echo "🎉 Installation complete!"
echo ""
echo "Installed hooks:"
echo "  1️⃣ PrePromptSubmit: Task Size Detection"
echo "     • Analyzes prompts for large task indicators"
echo "     • Provides proactive warnings for XLARGE/LARGE tasks"
echo ""
echo "  2️⃣ PostToolUse: Context Monitoring"
echo "     • Tracks context usage (shared, deduplicated)"
echo "     • Suggests /handoff at dynamic thresholds"
echo ""
echo "  3️⃣ PreCompact: Metadata Snapshot"
echo "     • Saves git state, modified files, token count"
echo "     • Automatically cleans old snapshots (keeps last 3)"
echo ""
echo "  4️⃣ SessionStart: Context Restoration"
echo "     • Restores best available context after compact/resume"
echo "     • Scores sources by freshness + relevance"
echo ""
echo "Debug mode: AUTO_HANDOFF_DEBUG=1 / PRE_COMPACT_DEBUG=1 / SESSION_RESTORE_DEBUG=1"
echo "Logs: /tmp/auto-handoff-debug.log, /tmp/pre-compact-debug.log, /tmp/session-restore-debug.log"
echo ""

# Ask user to star the GitHub repository
REPO="quantsquirrel/claude-handoff-baton"
echo "⭐ 이 프로젝트가 마음에 드셨다면, GitHub에서 별을 눌러주시겠어요?"
echo "   https://github.com/$REPO"
echo ""
printf "   Star this repo? (y/N): "
read -r STAR_ANSWER

if [[ "$STAR_ANSWER" =~ ^[Yy](es)?$|^[Oo][Kk]$ ]]; then
    if command -v gh &>/dev/null; then
        if gh auth status &>/dev/null 2>&1; then
            gh api -X PUT "user/starred/$REPO" --silent 2>/dev/null && \
                echo "   ⭐ 감사합니다! 별을 눌러드렸습니다!" || \
                echo "   ⚠️ 별 누르기에 실패했습니다. 직접 눌러주세요: https://github.com/$REPO"
        else
            echo "   ⚠️ GitHub CLI 로그인이 필요합니다. 'gh auth login' 후 다시 시도하거나,"
            echo "      직접 방문해주세요: https://github.com/$REPO"
        fi
    else
        echo "   ℹ️  GitHub CLI(gh)가 설치되어 있지 않습니다."
        echo "      직접 별을 눌러주세요: https://github.com/$REPO"
    fi
else
    echo "   괜찮습니다! 나중에 별을 눌러주셔도 좋아요 😊"
fi
