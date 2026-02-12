#!/usr/bin/env node
/**
 * Task Size Estimator Hook
 *
 * PrePromptSubmit hook that analyzes user requests
 * to estimate task size and provide proactive handoff recommendations.
 */

/**
 * NOTE: This implementation assumes single-node execution.
 * File locking uses local filesystem locks which are not
 * suitable for distributed/multi-node Claude Code deployments.
 */

import * as fs from 'fs';
import * as path from 'path';
import { tmpdir } from 'os';

import {
  TASK_SIZE,
  LARGE_TASK_KEYWORDS,
  TASK_SIZE_STATE_FILE,
} from './constants.mjs';

const STATE_FILE = path.join(tmpdir(), TASK_SIZE_STATE_FILE);
const LOCK_TIMEOUT_MS = 5000; // 5 seconds lock timeout

/**
 * Acquire file lock with timeout
 * @param {string} lockFile - Lock file path
 * @param {number} timeout - Timeout in ms
 * @returns {boolean} - True if lock acquired
 */
function acquireLock(lockFile, timeout = LOCK_TIMEOUT_MS) {
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    try {
      // Try to create lock file exclusively
      fs.writeFileSync(lockFile, String(process.pid), { flag: 'wx', mode: 0o600 });
      return true;
    } catch (e) {
      if (e.code === 'EEXIST') {
        // Check if lock is stale (older than timeout)
        try {
          const stat = fs.statSync(lockFile);
          if (Date.now() - stat.mtimeMs > timeout) {
            fs.unlinkSync(lockFile);
            continue;
          }
        } catch (statErr) {
          // Lock file was removed, retry
          continue;
        }
        // Wait a bit before retrying
        const waitStart = Date.now();
        while (Date.now() - waitStart < 50) { /* busy wait 50ms */ }
      } else {
        return false;
      }
    }
  }
  return false;
}

/**
 * Release file lock
 * @param {string} lockFile - Lock file path
 */
function releaseLock(lockFile) {
  try {
    fs.unlinkSync(lockFile);
  } catch (e) {
    // Ignore errors
  }
}

/**
 * Analyze prompt for task size indicators
 * @param {string} prompt - User prompt text
 * @returns {{ size: string, matches: string[] }}
 */
function analyzePrompt(prompt) {
  const promptLower = prompt.toLowerCase();
  let score = 0;
  const matches = [];

  for (const keyword of LARGE_TASK_KEYWORDS) {
    if (promptLower.includes(keyword.toLowerCase())) {
      score += 1;
      matches.push(keyword);
    }
  }

  // Determine size based on score
  if (score >= 4) return { size: TASK_SIZE.XLARGE, matches };
  if (score >= 2) return { size: TASK_SIZE.LARGE, matches };
  if (score >= 1) return { size: TASK_SIZE.MEDIUM, matches };
  return { size: TASK_SIZE.SMALL, matches };
}

/**
 * Load existing state with lock
 * @returns {object}
 */
function loadState() {
  try {
    if (fs.existsSync(STATE_FILE)) {
      const data = fs.readFileSync(STATE_FILE, 'utf8');
      return JSON.parse(data);
    }
  } catch (e) {
    // Return empty state on error
  }
  return {};
}

/**
 * Save state with lock to prevent race conditions
 * @param {string} sessionId - Session ID
 * @param {object} sessionData - Session data to save
 */
function saveTaskSizeState(sessionId, sessionData) {
  const lockFile = STATE_FILE + '.lock';

  if (!acquireLock(lockFile)) {
    console.error('[task-size-estimator] Failed to acquire lock');
    return;
  }

  try {
    // Load existing state
    const state = loadState();

    // Update session data
    state[sessionId] = {
      ...sessionData,
      updatedAt: Date.now(),
    };

    // Clean up old sessions (older than 1 hour)
    const oneHourAgo = Date.now() - (60 * 60 * 1000);
    for (const sid of Object.keys(state)) {
      if (state[sid].updatedAt && state[sid].updatedAt < oneHourAgo) {
        delete state[sid];
      }
    }

    // Write atomically by writing to temp file then renaming
    const tempFile = STATE_FILE + '.tmp';
    fs.writeFileSync(tempFile, JSON.stringify(state, null, 2), { mode: 0o600 });
    fs.renameSync(tempFile, STATE_FILE);
  } finally {
    releaseLock(lockFile);
  }
}

function main() {
  // Read hook input from stdin
  let input = '';
  try {
    input = fs.readFileSync(0, 'utf8');
  } catch (e) {
    return;
  }

  let hookData;
  try {
    hookData = JSON.parse(input);
  } catch (e) {
    return;
  }

  const { prompt, session_id } = hookData;
  if (!prompt || !session_id) return;

  const analysis = analyzePrompt(prompt);

  // Save to state for PostToolUse to read (with lock)
  saveTaskSizeState(session_id, {
    taskSize: analysis.size,
    matches: analysis.matches,
  });

  // Proactive message for large tasks
  if (analysis.size === TASK_SIZE.XLARGE) {
    console.log(JSON.stringify({
      decision: 'approve',
      additionalContext: `🔍 **대형 작업 감지** (키워드: ${analysis.matches.join(', ')})

이 작업은 많은 컨텍스트를 사용할 것으로 예상됩니다.

**권장 사항:**
- 작업 시작 전 현재 상태 handoff 생성: \`/handoff pre-work\`
- 또는 작업 분할을 고려하세요

진행하시겠습니까?`
    }));
  } else if (analysis.size === TASK_SIZE.LARGE) {
    console.log(JSON.stringify({
      decision: 'approve',
      additionalContext: `📋 **중대형 작업 감지** - 50% 컨텍스트 도달 시 handoff를 권장합니다.`
    }));
  }
}

main();
