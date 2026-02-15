#!/usr/bin/env node
/**
 * Pre-Compact Hook
 *
 * Saves a metadata snapshot before context compaction so that
 * session-restore can recover essential state.
 *
 * Works as a Claude Code PreCompact hook.
 * Note: PreCompact cannot block compaction (exit 2 only shows stderr).
 */

import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'node:child_process';

import {
  loadJsonState,
  createDebugLogger,
  getSharedTokenCount,
} from './utils.mjs';

import { TASK_SIZE_STATE_FILE } from './constants.mjs';

import { tmpdir } from 'os';

const debugLog = createDebugLogger(
  'pre-compact',
  path.join(tmpdir(), 'pre-compact-debug.log'),
  'PRE_COMPACT_DEBUG',
);

const SNAPSHOT_PREFIX = '.pre-compact-';

/**
 * Get git information for the snapshot
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
    const lastCommit = execSync('git log -1 --oneline 2>/dev/null', {
      encoding: 'utf8',
      cwd: process.cwd(),
    }).trim();
    return { branch, status, lastCommit };
  } catch (e) {
    return { branch: null, status: null, lastCommit: null };
  }
}

/**
 * Get list of modified files from git
 */
function getModifiedFiles() {
  try {
    const output = execSync('git diff --name-only 2>/dev/null', {
      encoding: 'utf8',
      cwd: process.cwd(),
    }).trim();
    return output ? output.split('\n') : [];
  } catch (e) {
    return [];
  }
}

/**
 * Clean up old snapshots (keep last 3)
 */
function cleanOldSnapshots(handoffDir) {
  try {
    const files = fs.readdirSync(handoffDir)
      .filter(f => f.startsWith(SNAPSHOT_PREFIX) && f.endsWith('.json'))
      .map(f => ({
        name: f,
        path: path.join(handoffDir, f),
        mtime: fs.statSync(path.join(handoffDir, f)).mtimeMs,
      }))
      .sort((a, b) => b.mtime - a.mtime);

    // Keep only the 3 most recent
    for (const file of files.slice(3)) {
      fs.unlinkSync(file.path);
      debugLog('Removed old snapshot:', file.name);
    }
  } catch (e) {
    debugLog('Error cleaning old snapshots:', e.message);
  }
}

function main() {
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

  const { session_id } = hookData;
  if (!session_id) return;

  debugLog('PreCompact triggered for session:', session_id);

  // Gather snapshot data
  const gitInfo = getGitInfo();
  const modifiedFiles = getModifiedFiles();
  const tokenCount = getSharedTokenCount(session_id);

  // Load task size if available
  const taskSizeStatePath = path.join(tmpdir(), TASK_SIZE_STATE_FILE);
  const taskSizeState = loadJsonState(taskSizeStatePath);
  const taskSize = taskSizeState[session_id]?.taskSize || 'medium';

  const snapshot = {
    snapshotType: 'pre-compact',
    sessionId: session_id,
    timestamp: new Date().toISOString(),
    cwd: process.cwd(),
    gitBranch: gitInfo.branch,
    gitStatus: gitInfo.status,
    lastCommit: gitInfo.lastCommit,
    modifiedFiles,
    estimatedTokens: tokenCount,
    taskSize,
  };

  // Save snapshot
  const handoffDir = path.join(process.cwd(), '.claude', 'handoffs');
  if (!fs.existsSync(handoffDir)) {
    fs.mkdirSync(handoffDir, { recursive: true });
  }

  const snapshotFile = path.join(
    handoffDir,
    `${SNAPSHOT_PREFIX}${Date.now()}.json`,
  );
  fs.writeFileSync(snapshotFile, JSON.stringify(snapshot, null, 2));
  debugLog('Snapshot saved:', snapshotFile);

  // Clean old snapshots
  cleanOldSnapshots(handoffDir);

  // Output confirmation (cannot block compaction)
  const result = {
    decision: 'approve',
  };
  console.log(JSON.stringify(result));
}

main();
