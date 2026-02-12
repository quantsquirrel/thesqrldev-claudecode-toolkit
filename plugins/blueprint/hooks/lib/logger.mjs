import { appendFileSync, mkdirSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';

/**
 * Find .blueprint directory (walk up from cwd to find .git or .blueprint).
 * @param {string} startDir - Starting directory
 * @returns {string} Absolute path to .blueprint/
 */
function findLogDir(startDir = process.cwd()) {
  let dir = startDir;
  const root = dirname(dir) === dir ? dir : '/';

  while (dir !== root) {
    if (existsSync(join(dir, '.blueprint'))) {
      return join(dir, '.blueprint');
    }
    if (existsSync(join(dir, '.git'))) {
      return join(dir, '.blueprint');
    }
    dir = dirname(dir);
  }

  // Fallback: use startDir
  return join(startDir, '.blueprint');
}

const LOG_LEVELS = { debug: 0, info: 1, warn: 2, error: 3 };
const isStrict = process.env.BLUEPRINT_HOOK_STRICT === '1';

/**
 * Append a log entry to .blueprint/debug.log
 * Format: [ISO timestamp] [LEVEL] [hookName] message
 * @param {string} level - Log level (debug, info, warn, error)
 * @param {string} hookName - Name of the hook
 * @param {string} message - Log message
 * @param {object|null} meta - Optional metadata to append as JSON
 */
export function log(level, hookName, message, meta = null) {
  try {
    const logDir = findLogDir();
    mkdirSync(logDir, { recursive: true });
    const logPath = join(logDir, 'debug.log');
    const timestamp = new Date().toISOString();
    let entry = `[${timestamp}] [${level.toUpperCase()}] [${hookName}] ${message}`;
    if (meta) entry += ` | ${JSON.stringify(meta)}`;
    appendFileSync(logPath, entry + '\n', 'utf-8');
  } catch {
    // Never throw from logger - that would break the hook
  }
}

/**
 * Log debug message
 * @param {string} hookName - Name of the hook
 * @param {string} msg - Log message
 * @param {object} meta - Optional metadata
 */
export function debug(hookName, msg, meta) {
  log('debug', hookName, msg, meta);
}

/**
 * Log info message
 * @param {string} hookName - Name of the hook
 * @param {string} msg - Log message
 * @param {object} meta - Optional metadata
 */
export function info(hookName, msg, meta) {
  log('info', hookName, msg, meta);
}

/**
 * Log warning message
 * @param {string} hookName - Name of the hook
 * @param {string} msg - Log message
 * @param {object} meta - Optional metadata
 */
export function warn(hookName, msg, meta) {
  log('warn', hookName, msg, meta);
}

/**
 * Log error. In strict mode, also write error to stderr and exit(1).
 * @param {string} hookName - Name of the hook
 * @param {string} msg - Log message
 * @param {object} meta - Optional metadata
 */
export function error(hookName, msg, meta) {
  log('error', hookName, msg, meta);
  if (isStrict) {
    process.stderr.write(`[BLUEPRINT ERROR] [${hookName}] ${msg}\n`);
    process.exit(1);
  }
}
