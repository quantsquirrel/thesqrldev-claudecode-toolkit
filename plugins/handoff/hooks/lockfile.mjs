/**
 * Lockfile Recovery Module
 *
 * Manages lock files to detect interrupted handoff generation.
 * Lock files help recover state when generation is interrupted by compact.
 */

import * as fs from 'fs';
import * as path from 'path';
import { homedir } from 'os';
import { LOCK_FILE_NAME } from './constants.mjs';

/**
 * Get lock file path
 */
function getLockFilePath() {
  const handoffDir = path.join(process.cwd(), '.claude', 'handoffs');
  const globalHandoffDir = path.join(homedir(), '.claude', 'handoffs');

  // Check local first, then global
  for (const dir of [handoffDir, globalHandoffDir]) {
    if (fs.existsSync(dir)) {
      return path.join(dir, LOCK_FILE_NAME);
    }
  }

  // Default to local if neither exists
  const dir = handoffDir;
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  return path.join(dir, LOCK_FILE_NAME);
}

/**
 * Create a lock file
 * @param {string} sessionId - Session identifier
 * @param {string} topic - Handoff topic
 * @returns {boolean} Success
 */
export function createLock(sessionId, topic) {
  try {
    const lockPath = getLockFilePath();
    const lockData = {
      sessionId,
      startTime: new Date().toISOString(),
      topic: topic || 'untitled',
    };
    fs.writeFileSync(lockPath, JSON.stringify(lockData, null, 2));
    return true;
  } catch (e) {
    console.error('Failed to create lock file:', e.message);
    return false;
  }
}

/**
 * Remove lock file
 * @returns {boolean} Success
 */
export function removeLock() {
  try {
    const lockPath = getLockFilePath();
    if (fs.existsSync(lockPath)) {
      fs.unlinkSync(lockPath);
    }
    return true;
  } catch (e) {
    console.error('Failed to remove lock file:', e.message);
    return false;
  }
}

/**
 * Check if lock file exists and read its contents
 * @returns {object|null} Lock data or null if not found
 */
export function checkLock() {
  try {
    const lockPath = getLockFilePath();
    if (fs.existsSync(lockPath)) {
      const data = fs.readFileSync(lockPath, 'utf8');
      return JSON.parse(data);
    }
  } catch (e) {
    console.error('Failed to read lock file:', e.message);
  }
  return null;
}
