#!/usr/bin/env node
/**
 * Auto-Handoff Hook
 *
 * Monitors context usage and suggests running /handoff when reaching 70%.
 * Works as a Claude Code PostToolUse hook.
 *
 * Usage:
 *   Add to ~/.claude/settings.json hooks section:
 *   {
 *     "hooks": {
 *       "PostToolUse": [{
 *         "matcher": "Read|Grep|Glob|Bash|WebFetch",
 *         "hooks": [{
 *           "type": "command",
 *           "command": "node ~/.claude/skills/handoff/hooks/auto-handoff.mjs"
 *         }]
 *       }]
 *     }
 *   }
 */

import * as fs from 'fs';
import * as path from 'path';
import { tmpdir, homedir } from 'os';
import { execSync } from 'node:child_process';

import {
  HANDOFF_THRESHOLD,
  WARNING_THRESHOLD,
  CRITICAL_THRESHOLD,
  HANDOFF_COOLDOWN_MS,
  MAX_SUGGESTIONS,
  CLAUDE_CONTEXT_LIMIT,
  CHARS_PER_TOKEN,
  HANDOFF_SUGGESTION_MESSAGE,
  HANDOFF_WARNING_MESSAGE,
  HANDOFF_CRITICAL_MESSAGE,
  AUTO_DRAFT_ENABLED,
  DRAFT_FILE_PREFIX,
  // Task size imports (v2.0)
  TASK_SIZE,
  TASK_SIZE_THRESHOLDS,
  FILE_COUNT_THRESHOLDS,
  TASK_SIZE_STATE_FILE,
} from './constants.mjs';

const DEBUG = process.env.AUTO_HANDOFF_DEBUG === '1';
const STATE_FILE = path.join(tmpdir(), 'auto-handoff-state.json');
const DEBUG_FILE = path.join(tmpdir(), 'auto-handoff-debug.log');

// Task size state file (shared with task-size-estimator.mjs)
const TASK_SIZE_STATE_PATH = path.join(tmpdir(), TASK_SIZE_STATE_FILE);
const LOCK_TIMEOUT_MS = 5000;

/**
 * Debug logging
 */
function debugLog(...args) {
  if (DEBUG) {
    const msg = `[${new Date().toISOString()}] [auto-handoff] ${args
      .map((a) => (typeof a === 'object' ? JSON.stringify(a, null, 2) : String(a)))
      .join(' ')}\n`;
    fs.appendFileSync(DEBUG_FILE, msg);
  }
}

/**
 * Load state from file
 */
function loadState() {
  try {
    if (fs.existsSync(STATE_FILE)) {
      const data = fs.readFileSync(STATE_FILE, 'utf8');
      return JSON.parse(data);
    }
  } catch (e) {
    debugLog('Failed to load state:', e.message);
  }
  return {
    sessions: {},
  };
}

/**
 * Save state to file
 */
function saveState(state) {
  try {
    fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
  } catch (e) {
    debugLog('Failed to save state:', e.message);
  }
}

/**
 * Acquire file lock with timeout
 */
function acquireLock(lockFile, timeout = LOCK_TIMEOUT_MS) {
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    try {
      fs.writeFileSync(lockFile, String(process.pid), { flag: 'wx', mode: 0o600 });
      return true;
    } catch (e) {
      if (e.code === 'EEXIST') {
        try {
          const stat = fs.statSync(lockFile);
          if (Date.now() - stat.mtimeMs > timeout) {
            fs.unlinkSync(lockFile);
            continue;
          }
        } catch (statErr) {
          continue;
        }
        const waitStart = Date.now();
        while (Date.now() - waitStart < 50) { /* busy wait */ }
      } else {
        return false;
      }
    }
  }
  return false;
}

/**
 * Release file lock
 */
function releaseLock(lockFile) {
  try {
    fs.unlinkSync(lockFile);
  } catch (e) {
    // Ignore
  }
}

/**
 * Load task size state for session
 */
function loadTaskSizeState(sessionId) {
  try {
    if (fs.existsSync(TASK_SIZE_STATE_PATH)) {
      const data = JSON.parse(fs.readFileSync(TASK_SIZE_STATE_PATH, 'utf8'));
      return data[sessionId] || { taskSize: TASK_SIZE.MEDIUM };
    }
  } catch (e) {
    debugLog('Failed to load task size state:', e.message);
  }
  return { taskSize: TASK_SIZE.MEDIUM };
}

/**
 * Save updated task size state with lock
 */
function saveTaskSizeState(sessionId, taskSize) {
  const lockFile = TASK_SIZE_STATE_PATH + '.lock';

  if (!acquireLock(lockFile)) {
    debugLog('Failed to acquire lock for task size state');
    return;
  }

  try {
    let state = {};
    try {
      if (fs.existsSync(TASK_SIZE_STATE_PATH)) {
        state = JSON.parse(fs.readFileSync(TASK_SIZE_STATE_PATH, 'utf8'));
      }
    } catch (e) {
      // Start fresh
    }

    state[sessionId] = {
      ...(state[sessionId] || {}),
      taskSize,
      updatedAt: Date.now(),
    };

    const tempFile = TASK_SIZE_STATE_PATH + '.tmp';
    fs.writeFileSync(tempFile, JSON.stringify(state, null, 2), { mode: 0o600 });
    fs.renameSync(tempFile, TASK_SIZE_STATE_PATH);
  } finally {
    releaseLock(lockFile);
  }
}

/**
 * Analyze Glob/Grep tool result for file count
 */
function analyzeToolResult(toolName, toolInput, toolResponse) {
  const toolLower = toolName.toLowerCase();

  if (toolLower === 'glob' || toolLower === 'grep') {
    // Count file matches (one file per line)
    const lines = toolResponse.split('\n').filter(l => l.trim());
    return { fileCount: lines.length };
  }

  return { fileCount: 0 };
}

/**
 * Upgrade task size based on file count
 */
function upgradeTaskSize(currentSize, fileCount) {
  if (fileCount >= FILE_COUNT_THRESHOLDS.XLARGE) return TASK_SIZE.XLARGE;
  if (fileCount >= FILE_COUNT_THRESHOLDS.LARGE) return TASK_SIZE.LARGE;
  if (fileCount >= FILE_COUNT_THRESHOLDS.MEDIUM) return TASK_SIZE.MEDIUM;
  return currentSize;
}

/**
 * Get thresholds for task size
 */
function getThresholds(taskSize) {
  return TASK_SIZE_THRESHOLDS[taskSize] || TASK_SIZE_THRESHOLDS[TASK_SIZE.MEDIUM];
}

/**
 * Get or create session state
 */
function getSessionState(state, sessionId) {
  if (!state.sessions[sessionId]) {
    state.sessions[sessionId] = {
      lastSuggestionTime: 0,
      suggestionCount: 0,
      estimatedTokens: 0,
      handoffCreated: false,
      draftSaved: false,
    };
  }
  return state.sessions[sessionId];
}

/**
 * Estimate tokens from text
 */
function estimateTokens(text) {
  return Math.ceil(text.length / CHARS_PER_TOKEN);
}

/**
 * Check if handoff was recently created
 */
function checkRecentHandoff() {
  const handoffDir = path.join(process.cwd(), '.claude', 'handoffs');
  const globalHandoffDir = path.join(homedir(), '.claude', 'handoffs');

  for (const dir of [handoffDir, globalHandoffDir]) {
    try {
      if (fs.existsSync(dir)) {
        const files = fs.readdirSync(dir);
        const now = Date.now();
        const fiveMinutes = 5 * 60 * 1000;

        for (const file of files) {
          if (file.endsWith('.md')) {
            const stat = fs.statSync(path.join(dir, file));
            if (now - stat.mtimeMs < fiveMinutes) {
              return true; // Handoff created within 5 minutes
            }
          }
        }
      }
    } catch (e) {
      debugLog('Error checking handoff dir:', e.message);
    }
  }
  return false;
}

/**
 * Get git information (simple)
 */
function getGitInfo() {
  try {
    const branch = execSync('git rev-parse --abbrev-ref HEAD 2>/dev/null', {
      encoding: 'utf8',
      cwd: process.cwd(),
    }).trim();
    const status = execSync('git status --short 2>/dev/null', {
      encoding: 'utf8',
      cwd: process.cwd(),
    }).trim();
    return { branch, status };
  } catch (e) {
    return { branch: null, status: null };
  }
}

/**
 * Save auto-draft at 70% threshold
 */
function saveDraft(sessionId, estimatedTokens) {
  if (!AUTO_DRAFT_ENABLED) {
    return;
  }

  try {
    const handoffDir = path.join(process.cwd(), '.claude', 'handoffs');
    if (!fs.existsSync(handoffDir)) {
      fs.mkdirSync(handoffDir, { recursive: true });
    }

    const timestamp = Date.now();
    const draftFile = path.join(handoffDir, `${DRAFT_FILE_PREFIX}${timestamp}.json`);

    const gitInfo = getGitInfo();
    const draftData = {
      sessionId,
      timestamp: new Date().toISOString(),
      estimatedTokens,
      cwd: process.cwd(),
      gitBranch: gitInfo.branch,
      gitStatus: gitInfo.status,
    };

    // Remove old draft files for this session
    try {
      const files = fs.readdirSync(handoffDir);
      for (const file of files) {
        if (file.startsWith(DRAFT_FILE_PREFIX) && file.endsWith('.json')) {
          const filePath = path.join(handoffDir, file);
          try {
            const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
            if (data.sessionId === sessionId) {
              fs.unlinkSync(filePath);
              debugLog('Removed old draft:', file);
            }
          } catch (e) {
            // Ignore invalid draft files
          }
        }
      }
    } catch (e) {
      debugLog('Error cleaning old drafts:', e.message);
    }

    fs.writeFileSync(draftFile, JSON.stringify(draftData, null, 2));
    debugLog('Draft saved:', draftFile);
  } catch (e) {
    debugLog('Failed to save draft:', e.message);
    // Don't fail the hook if draft save fails
  }
}

/**
 * Main hook function
 */
function main() {
  // Read hook input from stdin
  let input = '';
  try {
    input = fs.readFileSync(0, 'utf8');
  } catch (e) {
    // No input available
    debugLog('No stdin input');
    return;
  }

  let hookData;
  try {
    hookData = JSON.parse(input);
  } catch (e) {
    debugLog('Failed to parse hook input:', e.message);
    return;
  }

  const { tool_name, session_id, tool_response, tool_input } = hookData;

  if (!tool_response || !session_id) {
    return;
  }

  // Only process large output tools
  const toolLower = (tool_name || '').toLowerCase();
  const largeOutputTools = ['read', 'grep', 'glob', 'bash', 'webfetch'];
  if (!largeOutputTools.includes(toolLower)) {
    return;
  }

  // Load state
  const state = loadState();
  const sessionState = getSessionState(state, session_id);

  // Track cumulative tokens
  const responseTokens = estimateTokens(tool_response);
  sessionState.estimatedTokens += responseTokens;

  debugLog('Tracking output', {
    tool: toolLower,
    tokens: responseTokens,
    cumulative: sessionState.estimatedTokens,
  });

  // Calculate usage ratio
  const usageRatio = sessionState.estimatedTokens / CLAUDE_CONTEXT_LIMIT;

  // === Task Size Dynamic Thresholds (v2.0) ===
  // Load task size from PrePromptSubmit hook or default
  const taskSizeState = loadTaskSizeState(session_id);
  let currentTaskSize = taskSizeState.taskSize;

  // Analyze Glob/Grep results for file count
  const toolAnalysis = analyzeToolResult(tool_name, tool_input, tool_response);

  // Upgrade task size if many files found
  if (toolAnalysis.fileCount > 0) {
    const upgradedSize = upgradeTaskSize(currentTaskSize, toolAnalysis.fileCount);
    if (upgradedSize !== currentTaskSize) {
      debugLog('Task size upgraded:', currentTaskSize, '->', upgradedSize,
               'due to', toolAnalysis.fileCount, 'files');
      currentTaskSize = upgradedSize;
      saveTaskSizeState(session_id, currentTaskSize);
    }
  }

  // Get dynamic thresholds based on task size
  const dynamicThresholds = getThresholds(currentTaskSize);
  debugLog('Using thresholds for', currentTaskSize, ':', dynamicThresholds);

  // Save auto-draft at 70% threshold
  if (usageRatio >= HANDOFF_THRESHOLD && !sessionState.draftSaved) {
    saveDraft(session_id, sessionState.estimatedTokens);
    sessionState.draftSaved = true;
  }

  // Check if below threshold
  if (usageRatio < dynamicThresholds.handoff) {
    saveState(state);
    return;
  }

  // Check cooldown
  const now = Date.now();
  if (now - sessionState.lastSuggestionTime < HANDOFF_COOLDOWN_MS) {
    debugLog('Skipping - cooldown active');
    saveState(state);
    return;
  }

  // Check max suggestions
  if (sessionState.suggestionCount >= MAX_SUGGESTIONS) {
    debugLog('Skipping - max suggestions reached');
    saveState(state);
    return;
  }

  // Check if handoff was recently created
  if (checkRecentHandoff()) {
    debugLog('Skipping - recent handoff detected');
    sessionState.handoffCreated = true;
    saveState(state);
    return;
  }

  // Record suggestion
  sessionState.lastSuggestionTime = now;
  sessionState.suggestionCount++;
  saveState(state);

  // Determine message based on DYNAMIC threshold
  let message;
  if (usageRatio >= dynamicThresholds.critical) {
    message = HANDOFF_CRITICAL_MESSAGE;
  } else if (usageRatio >= dynamicThresholds.warning) {
    message = HANDOFF_WARNING_MESSAGE;
  } else if (usageRatio >= dynamicThresholds.handoff) {
    message = HANDOFF_SUGGESTION_MESSAGE;
  }

  // Add file count info for large tasks
  if (toolAnalysis.fileCount >= FILE_COUNT_THRESHOLDS.LARGE && message) {
    const sizeInfo = `📊 **${toolAnalysis.fileCount}개 파일 발견** - 작업 크기: ${currentTaskSize.toUpperCase()}
임계값 조정됨: ${Math.round(dynamicThresholds.handoff * 100)}%에서 handoff 권장

`;
    message = sizeInfo + message;
  }

  // Output message as hook result
  const result = {
    decision: 'approve',
    additionalContext: message,
  };

  console.log(JSON.stringify(result));
}

main();
