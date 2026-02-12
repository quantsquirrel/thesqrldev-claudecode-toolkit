import { readFileSync, writeFileSync, mkdirSync, renameSync, unlinkSync, existsSync, statSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { homedir, hostname } from 'node:os';
import { randomBytes } from 'node:crypto';

/**
 * Walk up from cwd to find .blueprint/ directory or git root.
 * Creates .blueprint/ if needed.
 * @returns {string} Absolute path to .blueprint/
 */
export function findBlueprintRoot(startDir = process.cwd()) {
  let dir = startDir;
  const root = dirname(dir) === dir ? dir : '/';

  while (dir !== root) {
    if (existsSync(join(dir, '.blueprint'))) {
      const blueprintDir = join(dir, '.blueprint');
      ensureDir(blueprintDir);
      return blueprintDir;
    }
    if (existsSync(join(dir, '.git'))) {
      const blueprintDir = join(dir, '.blueprint');
      ensureDir(blueprintDir);
      return blueprintDir;
    }
    dir = dirname(dir);
  }

  // Fallback: use cwd
  const blueprintDir = join(startDir, '.blueprint');
  ensureDir(blueprintDir);
  return blueprintDir;
}

/**
 * Recursively create directory if it doesn't exist.
 * @param {string} dirPath - Absolute directory path
 */
export function ensureDir(dirPath) {
  mkdirSync(dirPath, { recursive: true });
}

/**
 * Generate a short unique ID: timestamp + random hex.
 * Example: "20260210-a3f2b1"
 * @returns {string}
 */
export function generateId() {
  const now = new Date();
  const date = now.toISOString().slice(0, 10).replace(/-/g, '');
  const rand = randomBytes(3).toString('hex');
  return `${date}-${rand}`;
}

/**
 * Read and parse a JSON state file.
 * @param {string} filePath - Absolute path to JSON file
 * @returns {object|null} Parsed data or null if not found / invalid
 */
export function loadState(filePath) {
  try {
    const raw = readFileSync(filePath, 'utf-8');
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/**
 * Atomic write: write to temp file, then rename.
 * @param {string} filePath - Absolute path for the state file
 * @param {object} data - Data to serialize as JSON
 */
export function saveState(filePath, data) {
  ensureDir(dirname(filePath));
  const tmpPath = `${filePath}.tmp.${process.pid}`;
  try {
    writeFileSync(tmpPath, JSON.stringify(data, null, 2) + '\n', 'utf-8');
    renameSync(tmpPath, filePath);
  } catch (err) {
    // Clean up temp file on failure
    try { unlinkSync(tmpPath); } catch { /* ignore */ }
    throw err;
  }
}

/**
 * Check if a process with the given PID is still running.
 * @param {number} pid
 * @returns {boolean}
 */
function isProcessRunning(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

/**
 * Acquire a file lock for concurrent access protection.
 * Lock file: {filePath}.lock containing JSON with pid, timestamp, hostname.
 *
 * - If lock exists and is stale (>30s or PID dead), remove and acquire.
 * - If lock exists and is fresh, retry up to 5s.
 * - Returns lock info on success, null on timeout (stale data mode).
 *
 * @param {string} filePath - Path of the file to lock
 * @param {object} [options]
 * @param {number} [options.timeoutMs=5000] - Max wait time
 * @param {number} [options.staleMs=30000] - Age after which lock is considered stale
 * @returns {object|null} Lock info or null if acquisition failed
 */
export function acquireLock(filePath, options = {}) {
  const { timeoutMs = 5000, staleMs = 30000 } = options;
  const lockPath = `${filePath}.lock`;
  const lockData = {
    pid: process.pid,
    timestamp: new Date().toISOString(),
    hostname: hostname()
  };

  const deadline = Date.now() + timeoutMs;
  const retryIntervalMs = 100;

  while (true) {
    // Try to check existing lock
    const existing = loadState(lockPath);

    if (existing) {
      const lockAge = Date.now() - new Date(existing.timestamp).getTime();
      const pidDead = !isProcessRunning(existing.pid);

      if (lockAge > staleMs || pidDead) {
        // Stale lock -- remove it
        try { unlinkSync(lockPath); } catch { /* ignore */ }
      } else {
        // Lock is fresh and held by a running process
        if (Date.now() >= deadline) {
          return null; // Timeout -- stale data mode
        }
        // Busy-wait with sleep
        sleepSync(retryIntervalMs);
        continue;
      }
    }

    // Attempt to create lock file
    try {
      writeFileSync(lockPath, JSON.stringify(lockData, null, 2) + '\n', {
        flag: 'wx' // Exclusive create -- fails if file exists
      });
      return lockData;
    } catch (err) {
      if (err.code === 'EEXIST') {
        // Race condition -- another process created the lock between our check and write
        if (Date.now() >= deadline) {
          return null;
        }
        sleepSync(retryIntervalMs);
        continue;
      }
      throw err;
    }
  }
}

/**
 * Release a file lock.
 * @param {string} filePath - Path of the file whose lock to release
 */
export function releaseLock(filePath) {
  const lockPath = `${filePath}.lock`;
  try {
    unlinkSync(lockPath);
  } catch {
    // Lock already removed -- not an error
  }
}

/**
 * Move a state file to a history directory with timestamp suffix.
 * @param {string} fromPath - Source file path
 * @param {string} toDir - Destination directory
 * @returns {string} Path to the archived file
 */
export function archiveState(fromPath, toDir) {
  ensureDir(toDir);
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const baseName = fromPath.split('/').pop().replace('.json', '');
  const archivePath = join(toDir, `${baseName}-${timestamp}.json`);

  const data = loadState(fromPath);
  if (data) {
    saveState(archivePath, data);
    try { unlinkSync(fromPath); } catch { /* ignore */ }
  }
  return archivePath;
}

/**
 * Check if state data belongs to a specific session.
 * @param {object} stateData - State object with a sessionId field
 * @param {string} sessionId - Expected session ID
 * @returns {boolean}
 */
export function isSessionMatch(stateData, sessionId) {
  if (!stateData || !sessionId) return false;
  return stateData.sessionId === sessionId;
}

/**
 * Check if state data is older than a maximum age.
 * @param {object} stateData - State object with an updatedAt or createdAt field
 * @param {number} maxAgeMs - Maximum age in milliseconds
 * @returns {boolean} True if state is stale
 */
export function checkStaleness(stateData, maxAgeMs) {
  if (!stateData) return true;
  const timestamp = stateData.updatedAt || stateData.createdAt;
  if (!timestamp) return true;
  return (Date.now() - new Date(timestamp).getTime()) > maxAgeMs;
}

/**
 * Read the active items index file (e.g., active-cycles.json).
 * @param {string} indexPath - Absolute path to the index JSON file
 * @returns {object} Index data (defaults to empty object with items array)
 */
export function listActiveItems(indexPath) {
  const data = loadState(indexPath);
  return data || { items: [] };
}

/**
 * Lock-protected read-modify-write of an index file.
 * @param {string} indexPath - Absolute path to the index JSON file
 * @param {string} id - Item ID to update
 * @param {object} data - Data to set for this item (null to remove)
 */
export function updateIndex(indexPath, id, data) {
  const lock = acquireLock(indexPath);

  try {
    const index = loadState(indexPath) || { items: [] };

    const existingIdx = index.items.findIndex((item) => item.id === id);

    if (data === null) {
      // Remove item
      if (existingIdx !== -1) {
        index.items.splice(existingIdx, 1);
      }
    } else if (existingIdx !== -1) {
      // Update existing
      index.items[existingIdx] = { id, ...data, updatedAt: new Date().toISOString() };
    } else {
      // Add new
      index.items.push({ id, ...data, createdAt: new Date().toISOString() });
    }

    index.updatedAt = new Date().toISOString();
    saveState(indexPath, index);
  } finally {
    if (lock) {
      releaseLock(indexPath);
    }
  }
}

/**
 * Synchronous sleep using Atomics.wait on a SharedArrayBuffer.
 * @param {number} ms - Milliseconds to sleep
 */
function sleepSync(ms) {
  const buf = new SharedArrayBuffer(4);
  const arr = new Int32Array(buf);
  Atomics.wait(arr, 0, 0, ms);
}
