/**
 * Shared Utilities for Handoff Hooks
 *
 * Consolidates duplicated logic from auto-handoff.mjs, auto-checkpoint.mjs,
 * and task-size-estimator.mjs into a single module.
 *
 * Provides: file locking, JSON state I/O, token estimation, debug logging.
 */

import * as fs from 'fs';
import { CHARS_PER_TOKEN, SHARED_TOKEN_STATE_FILE } from './constants.mjs';
import * as path from 'path';
import { tmpdir } from 'os';

const SHARED_TOKEN_STATE_PATH = path.join(tmpdir(), SHARED_TOKEN_STATE_FILE);

/** Default lock acquisition timeout (ms) */
export const DEFAULT_LOCK_TIMEOUT_MS = 5000;

/**
 * Acquire an exclusive file lock with timeout.
 * Uses atomic file creation (wx flag) and stale lock detection.
 *
 * @param {string} lockFile - Path to the lock file
 * @param {number} [timeout=DEFAULT_LOCK_TIMEOUT_MS] - Max wait time in ms
 * @returns {boolean} True if lock acquired
 */
export function acquireLock(lockFile, timeout = DEFAULT_LOCK_TIMEOUT_MS) {
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
 * Release a file lock.
 *
 * @param {string} lockFile - Path to the lock file
 */
export function releaseLock(lockFile) {
  try {
    fs.unlinkSync(lockFile);
  } catch (e) {
    // Ignore - lock may already be removed
  }
}

/**
 * Load JSON state from a file.
 *
 * @param {string} filePath - Path to the JSON state file
 * @param {*} [defaultValue={}] - Value to return if file missing or corrupt
 * @returns {*} Parsed JSON or defaultValue
 */
export function loadJsonState(filePath, defaultValue = {}) {
  try {
    if (fs.existsSync(filePath)) {
      const data = fs.readFileSync(filePath, 'utf8');
      return JSON.parse(data);
    }
  } catch (e) {
    // Return default on any read/parse error
  }
  return defaultValue;
}

/**
 * Save JSON state to a file.
 *
 * @param {string} filePath - Path to the JSON state file
 * @param {*} data - Data to serialize
 */
export function saveJsonState(filePath, data) {
  try {
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
  } catch (e) {
    // Silently fail - caller can check via debugLog
  }
}

/**
 * Save JSON state atomically (write to .tmp then rename).
 * Should be used with acquireLock/releaseLock for concurrent access.
 *
 * @param {string} filePath - Path to the JSON state file
 * @param {*} data - Data to serialize
 */
export function saveJsonStateAtomic(filePath, data) {
  const tempFile = filePath + '.tmp';
  fs.writeFileSync(tempFile, JSON.stringify(data, null, 2), { mode: 0o600 });
  fs.renameSync(tempFile, filePath);
}

/**
 * Estimate token count from text length.
 *
 * @param {string} text - Input text
 * @returns {number} Estimated token count
 */
export function estimateTokens(text) {
  return Math.ceil(text.length / CHARS_PER_TOKEN);
}

/**
 * Create a scoped debug logger.
 * Logging is enabled when the specified env var is set to '1'.
 *
 * @param {string} name - Logger name (appears in log prefix)
 * @param {string} debugFile - Path to the debug log file
 * @param {string} envVar - Environment variable that enables logging
 * @returns {function(...args): void} Debug logging function
 */
export function createDebugLogger(name, debugFile, envVar) {
  const enabled = process.env[envVar] === '1';

  return function debugLog(...args) {
    if (!enabled) return;
    const msg = `[${new Date().toISOString()}] [${name}] ${args
      .map((a) => (typeof a === 'object' ? JSON.stringify(a, null, 2) : String(a)))
      .join(' ')}\n`;
    fs.appendFileSync(debugFile, msg);
  };
}

/**
 * Get current cumulative token count for a session (read-only, no lock).
 *
 * @param {string} sessionId - Session identifier
 * @returns {number} Current cumulative estimated token count
 */
export function getSharedTokenCount(sessionId) {
  const state = loadJsonState(SHARED_TOKEN_STATE_PATH);
  return state[sessionId]?.estimatedTokens || 0;
}

/**
 * Track token usage in a shared state file with call-level deduplication.
 *
 * Multiple hooks may fire for the same tool call (e.g. Read triggers both
 * auto-handoff and auto-checkpoint). This function uses a callId fingerprint
 * (toolName:responseLength) to ensure each call's tokens are counted only once.
 *
 * @param {string} sessionId - Session identifier
 * @param {string} toolName - Name of the tool that produced the response
 * @param {string} toolResponse - The tool response text
 * @returns {number} Current cumulative estimated token count for the session
 */
export function trackTokenUsage(sessionId, toolName, toolResponse) {
  const lockFile = SHARED_TOKEN_STATE_PATH + '.lock';
  const responseTokens = estimateTokens(toolResponse);
  const callId = `${toolName}:${toolResponse.length}`;

  if (!acquireLock(lockFile)) {
    // Can't lock - return best-effort estimate from file
    const state = loadJsonState(SHARED_TOKEN_STATE_PATH);
    return (state[sessionId]?.estimatedTokens || 0) + responseTokens;
  }

  try {
    const state = loadJsonState(SHARED_TOKEN_STATE_PATH);
    const session = state[sessionId] || { estimatedTokens: 0 };

    // Dedup: skip if this exact call was already counted by another hook
    if (session.lastCallId !== callId) {
      session.estimatedTokens += responseTokens;
      session.lastCallId = callId;
      session.updatedAt = Date.now();
    }

    state[sessionId] = session;
    saveJsonStateAtomic(SHARED_TOKEN_STATE_PATH, state);

    return session.estimatedTokens;
  } finally {
    releaseLock(lockFile);
  }
}
