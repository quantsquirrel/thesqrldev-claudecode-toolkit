#!/usr/bin/env node
/**
 * Auto-Checkpoint Hook
 *
 * Triggers automatic checkpoints based on:
 * - Time (every 30 minutes of active work)
 * - Token usage (at 70% capacity)
 * - Significant events
 *
 * Works as a Claude Code PostToolUse hook.
 *
 * Usage:
 *   Add to ~/.claude/settings.json hooks section:
 *   {
 *     "hooks": {
 *       "PostToolUse": [{
 *         "matcher": "Read|Edit|Write|Bash",
 *         "hooks": [{
 *           "type": "command",
 *           "command": "node ~/.claude/skills/handoff/hooks/auto-checkpoint.mjs"
 *         }]
 *       }]
 *     }
 *   }
 */

import * as fs from 'fs';
import * as path from 'path';
import { tmpdir } from 'os';

import {
  HANDOFF_THRESHOLD,
  CLAUDE_CONTEXT_LIMIT,
  CHARS_PER_TOKEN,
} from './constants.mjs';

// Configuration
const CONFIG = {
  intervalMinutes: 30,
  tokenThreshold: HANDOFF_THRESHOLD, // 0.70
  checkpointDir: '.claude/handoffs',
  cooldownMinutes: 25, // Don't checkpoint more often than this
};

const DEBUG = process.env.AUTO_CHECKPOINT_DEBUG === '1';
const STATE_FILE = path.join(tmpdir(), 'auto-checkpoint-state.json');
const DEBUG_FILE = path.join(tmpdir(), 'auto-checkpoint-debug.log');

/**
 * Debug logging
 */
function debugLog(...args) {
  if (DEBUG) {
    const msg = `[${new Date().toISOString()}] [auto-checkpoint] ${args
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
 * Get or create session state
 */
function getSessionState(state, sessionId) {
  if (!state.sessions[sessionId]) {
    state.sessions[sessionId] = {
      lastCheckpointTime: Date.now(),
      estimatedTokens: 0,
      startTime: Date.now(),
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
 * Check if checkpoint was recently created
 */
function checkRecentCheckpoint() {
  const checkpointDir = path.join(process.cwd(), CONFIG.checkpointDir);

  try {
    if (fs.existsSync(checkpointDir)) {
      const files = fs.readdirSync(checkpointDir);
      const now = Date.now();
      const cooldown = CONFIG.cooldownMinutes * 60 * 1000;

      for (const file of files) {
        if (file.startsWith('checkpoint-') && file.endsWith('.md')) {
          const stat = fs.statSync(path.join(checkpointDir, file));
          if (now - stat.mtimeMs < cooldown) {
            return true;
          }
        }
      }
    }
  } catch (e) {
    debugLog('Error checking checkpoint dir:', e.message);
  }
  return false;
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

  const { tool_name, session_id, tool_response } = hookData;

  if (!session_id) {
    return;
  }

  // Load state
  const state = loadState();
  const sessionState = getSessionState(state, session_id);

  // Track cumulative tokens if we have tool response
  if (tool_response) {
    const responseTokens = estimateTokens(tool_response);
    sessionState.estimatedTokens += responseTokens;
  }

  const now = Date.now();
  const timeSinceLastCheckpoint = now - sessionState.lastCheckpointTime;
  const intervalMs = CONFIG.intervalMinutes * 60 * 1000;
  const usageRatio = sessionState.estimatedTokens / CLAUDE_CONTEXT_LIMIT;

  debugLog('Checkpoint check', {
    tool: tool_name,
    timeSinceCheckpoint: Math.floor(timeSinceLastCheckpoint / 1000 / 60) + 'min',
    usageRatio: (usageRatio * 100).toFixed(1) + '%',
  });

  // Check if checkpoint needed
  let shouldCheckpoint = false;
  let reason = '';

  // Time-based trigger (30 minutes)
  if (timeSinceLastCheckpoint >= intervalMs) {
    shouldCheckpoint = true;
    reason = `${CONFIG.intervalMinutes}분 경과`;
  }

  // Token-based trigger (70%)
  if (usageRatio >= CONFIG.tokenThreshold) {
    shouldCheckpoint = true;
    reason = reason
      ? `${reason}, 토큰 사용량 ${(usageRatio * 100).toFixed(0)}%`
      : `토큰 사용량 ${(usageRatio * 100).toFixed(0)}%`;
  }

  if (!shouldCheckpoint) {
    saveState(state);
    return;
  }

  // Check recent checkpoint (cooldown)
  if (checkRecentCheckpoint()) {
    debugLog('Skipping - recent checkpoint exists');
    saveState(state);
    return;
  }

  // Update checkpoint time
  sessionState.lastCheckpointTime = now;
  saveState(state);

  // Output checkpoint trigger message
  const message = `\n🔖 자동 체크포인트 트리거 (${reason})\n`;

  const result = {
    decision: 'approve',
    additionalContext: message + 'Silent checkpoint 실행을 권장합니다: /handoff checkpoint --silent',
  };

  console.log(JSON.stringify(result));
}

main();
