#!/usr/bin/env node

/**
 * Cycle Finalize Hook (Stop) — CommonJS
 * Suspends active PDCA cycles and pipeline runs when the session stops.
 * Must be CJS because Stop hooks require synchronous-style execution.
 *
 * Pattern: blueprint persistent-mode
 *
 * NOTE: state-manager.mjs is ESM, so we cannot require() it.
 * We implement the needed file operations directly using Node.js builtins.
 */

const {
  existsSync,
  readFileSync,
  writeFileSync,
  mkdirSync,
  readdirSync,
  renameSync,
  unlinkSync
} = require('fs');
const { join, dirname } = require('path');

// Inline logging function for CJS (cannot import from logger.mjs)
function logError(hookName, message, meta) {
  try {
    const logDir = findBlueprintDir(process.cwd());
    if (!existsSync(logDir)) mkdirSync(logDir, { recursive: true });
    const logPath = join(logDir, 'debug.log');
    const timestamp = new Date().toISOString();
    let entry = `[${timestamp}] [ERROR] [${hookName}] ${message}`;
    if (meta) entry += ` | ${JSON.stringify(meta)}`;
    writeFileSync(logPath, entry + '\n', { flag: 'a', encoding: 'utf-8' });

    // Check strict mode
    if (process.env.BLUEPRINT_HOOK_STRICT === '1') {
      process.stderr.write(`[BLUEPRINT ERROR] [${hookName}] ${message}\n`);
      process.exit(1);
    }
  } catch {
    // Never throw from logger
  }
}

function logInfo(hookName, message) {
  try {
    const logDir = findBlueprintDir(process.cwd());
    if (!existsSync(logDir)) mkdirSync(logDir, { recursive: true });
    const logPath = join(logDir, 'debug.log');
    const timestamp = new Date().toISOString();
    const entry = `[${timestamp}] [INFO] [${hookName}] ${message}\n`;
    writeFileSync(logPath, entry, { flag: 'a', encoding: 'utf-8' });
  } catch {
    // Never throw from logger
  }
}

// Inline readStdin for CJS
async function readStdin(timeoutMs = 5000) {
  return new Promise((resolve) => {
    const chunks = [];
    let settled = false;
    const timeout = setTimeout(() => {
      if (!settled) {
        settled = true;
        process.stdin.removeAllListeners();
        try { process.stdin.destroy(); } catch { /* ignore */ }
        resolve(Buffer.concat(chunks).toString('utf-8'));
      }
    }, timeoutMs);
    process.stdin.on('data', (chunk) => { chunks.push(chunk); });
    process.stdin.on('end', () => {
      if (!settled) { settled = true; clearTimeout(timeout); resolve(Buffer.concat(chunks).toString('utf-8')); }
    });
    process.stdin.on('error', () => {
      if (!settled) { settled = true; clearTimeout(timeout); resolve(''); }
    });
    if (process.stdin.readableEnded) {
      if (!settled) { settled = true; clearTimeout(timeout); resolve(Buffer.concat(chunks).toString('utf-8')); }
    }
  });
}

// Inline JSON file helpers (since we can't import state-manager.mjs)
function readJsonFile(filePath) {
  try {
    if (!existsSync(filePath)) return null;
    return JSON.parse(readFileSync(filePath, 'utf-8'));
  } catch {
    return null;
  }
}

function writeJsonFile(filePath, data) {
  try {
    const dir = dirname(filePath);
    if (dir && dir !== '.' && !existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }
    const tmpPath = `${filePath}.tmp.${process.pid}`;
    writeFileSync(tmpPath, JSON.stringify(data, null, 2) + '\n', 'utf-8');
    renameSync(tmpPath, filePath);
    return true;
  } catch {
    return false;
  }
}

// Walk up from startDir to find .blueprint/ or .git/ root, return .blueprint/ path
function findBlueprintDir(startDir) {
  let dir = startDir;
  const root = '/';

  while (dir !== root) {
    if (existsSync(join(dir, '.blueprint'))) {
      const bp = join(dir, '.blueprint');
      if (!existsSync(bp)) mkdirSync(bp, { recursive: true });
      return bp;
    }
    if (existsSync(join(dir, '.git'))) {
      const bp = join(dir, '.blueprint');
      if (!existsSync(bp)) mkdirSync(bp, { recursive: true });
      return bp;
    }
    dir = dirname(dir);
  }

  // Fallback: use startDir
  const bp = join(startDir, '.blueprint');
  if (!existsSync(bp)) mkdirSync(bp, { recursive: true });
  return bp;
}

// Suspend all active PDCA cycles
function suspendPdcaCycles(blueprintDir) {
  const cyclesDir = join(blueprintDir, 'pdca', 'cycles');
  if (!existsSync(cyclesDir)) return 0;

  let count = 0;
  try {
    const files = readdirSync(cyclesDir).filter(f => f.endsWith('.json') && !f.endsWith('.lock'));
    for (const file of files) {
      const filePath = join(cyclesDir, file);
      const state = readJsonFile(filePath);
      if (state && state.status === 'active') {
        state.status = 'suspended';
        state.suspendedAt = new Date().toISOString();
        state.updatedAt = new Date().toISOString();
        writeJsonFile(filePath, state);
        count++;
      }
    }
  } catch { /* ignore */ }
  return count;
}

// Suspend all active pipeline runs
function suspendPipelineRuns(blueprintDir) {
  const runsDir = join(blueprintDir, 'pipeline', 'runs');
  if (!existsSync(runsDir)) return 0;

  let count = 0;
  try {
    const files = readdirSync(runsDir).filter(f => f.endsWith('.json') && !f.endsWith('.lock'));
    for (const file of files) {
      const filePath = join(runsDir, file);
      const state = readJsonFile(filePath);
      if (state && state.status === 'running') {
        state.status = 'paused';
        state.suspendedAt = new Date().toISOString();
        state.updatedAt = new Date().toISOString();
        writeJsonFile(filePath, state);
        count++;
      }
    }
  } catch { /* ignore */ }
  return count;
}

// Suspend active gap analyses
function suspendGapAnalyses(blueprintDir) {
  const analysesDir = join(blueprintDir, 'gaps', 'analyses');
  if (!existsSync(analysesDir)) return 0;

  let count = 0;
  try {
    const files = readdirSync(analysesDir).filter(f => f.endsWith('.json') && !f.endsWith('.lock'));
    for (const file of files) {
      const filePath = join(analysesDir, file);
      const state = readJsonFile(filePath);
      if (state && state.status === 'active') {
        state.status = 'suspended';
        state.suspendedAt = new Date().toISOString();
        state.updatedAt = new Date().toISOString();
        writeJsonFile(filePath, state);
        count++;
      }
    }
  } catch { /* ignore */ }
  return count;
}

async function main() {
  logInfo('cycle-finalize', 'Hook started');
  try {
    const input = await readStdin();
    let data = {};
    try { data = JSON.parse(input); } catch { /* ignore */ }

    const directory = data.cwd || data.directory || process.cwd();

    let blueprintDir;
    try {
      blueprintDir = findBlueprintDir(directory);
    } catch {
      console.log(JSON.stringify({ continue: true }));
      return;
    }

    // Suspend all active states
    const suspendedCycles = suspendPdcaCycles(blueprintDir);
    const suspendedRuns = suspendPipelineRuns(blueprintDir);
    const suspendedGaps = suspendGapAnalyses(blueprintDir);
    const totalSuspended = suspendedCycles + suspendedRuns + suspendedGaps;

    if (totalSuspended > 0) {
      // Write a suspension summary for debugging
      const summary = {
        timestamp: new Date().toISOString(),
        suspendedCycles,
        suspendedRuns,
        suspendedGaps,
        totalSuspended
      };
      try {
        writeJsonFile(join(blueprintDir, '.last-suspension.json'), summary);
      } catch { /* ignore */ }
    }

    // Always allow stop — never block
    console.log(JSON.stringify({ continue: true }));
  } catch (err) {
    logError('cycle-finalize', `Unexpected error: ${err?.message || err}`, { stack: err?.stack });
    console.log(JSON.stringify({ continue: true }));
  }
}

main();
