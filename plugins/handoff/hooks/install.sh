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
if grep -q "auto-handoff.mjs" "$SETTINGS_FILE" 2>/dev/null && grep -q "task-size-estimator.mjs" "$SETTINGS_FILE" 2>/dev/null; then
    echo "✅ Auto-handoff hooks are already installed!"
    echo ""
    echo "Installed hooks:"
    echo "  • PrePromptSubmit: task-size-estimator.mjs (task size detection)"
    echo "  • PostToolUse: auto-handoff.mjs (context monitoring)"
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

# Use Node.js to safely merge the hook configuration
node -e "
const fs = require('fs');
const settingsFile = '$SETTINGS_FILE';
const autoHandoffPath = '$AUTO_HANDOFF_PATH';
const taskSizePath = '$TASK_SIZE_PATH';

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
echo "     • Dynamically adjusts handoff thresholds"
echo ""
echo "  2️⃣ PostToolUse: Context Monitoring"
echo "     • Tracks context usage across tools"
echo "     • Suggests /handoff at dynamic thresholds:"
echo "       - Small tasks: 85% / 90% / 95%"
echo "       - Medium tasks: 70% / 80% / 90%"
echo "       - Large tasks: 50% / 60% / 70%"
echo "       - XLarge tasks: 30% / 40% / 50%"
echo ""
echo "To test, use Claude Code until context fills up."
echo ""
echo "Debug mode: AUTO_HANDOFF_DEBUG=1"
echo "Logs: /tmp/auto-handoff-debug.log"
