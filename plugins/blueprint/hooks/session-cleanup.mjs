#!/usr/bin/env node

/**
 * Session Cleanup Hook (SessionEnd)
 * Archives active states, removes stale locks, and cleans up orphaned files.
 *
 * Pattern: blueprint session-end
 */

import { existsSync, readdirSync, unlinkSync, statSync } from 'node:fs';
import { join } from 'node:path';
import {
  findBlueprintRoot,
  loadState,
  archiveState,
  checkStaleness,
  ensureDir
} from './lib/state-manager.mjs';
import { STATE_PATHS, CYCLE_STATUS, RUN_STATUS } from './lib/constants.mjs';
import { readStdin } from './lib/io.mjs';
import { error, info } from './lib/logger.mjs';

// Max age for stale locks: 2 minutes
const STALE_LOCK_AGE_MS = 2 * 60 * 1000;
// Max age for orphan detection: 48 hours
const ORPHAN_MAX_AGE_MS = 48 * 60 * 60 * 1000;

// Remove all .lock files in a directory
function removeAllLocks(dirPath) {
  if (!existsSync(dirPath)) return;
  try {
    const files = readdirSync(dirPath).filter(f => f.endsWith('.lock'));
    for (const file of files) {
      try { unlinkSync(join(dirPath, file)); } catch { /* ignore */ }
    }
  } catch { /* ignore */ }
}

// Archive completed/cancelled state files
function archiveCompletedStates(dirPath, historyDir, completedStatuses) {
  if (!existsSync(dirPath)) return;
  try {
    const files = readdirSync(dirPath).filter(f => f.endsWith('.json') && !f.endsWith('.lock'));
    for (const file of files) {
      const filePath = join(dirPath, file);
      const state = loadState(filePath);
      if (state && completedStatuses.includes(state.status)) {
        archiveState(filePath, historyDir);
      }
    }
  } catch { /* ignore */ }
}

// Clean up orphaned state files (excessively old)
function cleanOrphanedFiles(dirPath, historyDir) {
  if (!existsSync(dirPath)) return;
  try {
    const files = readdirSync(dirPath).filter(f => f.endsWith('.json') && !f.endsWith('.lock'));
    for (const file of files) {
      const filePath = join(dirPath, file);
      const state = loadState(filePath);
      if (state && checkStaleness(state, ORPHAN_MAX_AGE_MS)) {
        archiveState(filePath, historyDir);
      }
    }
  } catch { /* ignore */ }
}

// Remove stale temp files (*.tmp.*)
function cleanTempFiles(dirPath) {
  if (!existsSync(dirPath)) return;
  try {
    const files = readdirSync(dirPath).filter(f => f.includes('.tmp.'));
    const now = Date.now();
    for (const file of files) {
      const filePath = join(dirPath, file);
      try {
        const stat = statSync(filePath);
        // Remove temp files older than 5 minutes
        if (now - stat.mtimeMs > 5 * 60 * 1000) {
          unlinkSync(filePath);
        }
      } catch { /* ignore */ }
    }
  } catch { /* ignore */ }
}

async function main() {
  info('session-cleanup', 'Hook started');
  try {
    const input = await readStdin();
    let data = {};
    try { data = JSON.parse(input); } catch { /* ignore */ }

    const directory = data.cwd || data.directory || process.cwd();

    let blueprintDir;
    try {
      blueprintDir = findBlueprintRoot(directory);
    } catch {
      process.stdout.write(JSON.stringify({ continue: true }));
      return;
    }

    const pdcaCyclesDir = join(blueprintDir, STATE_PATHS.pdca.cycles);
    const pdcaHistoryDir = join(blueprintDir, STATE_PATHS.pdca.history);
    const pipelineRunsDir = join(blueprintDir, STATE_PATHS.pipeline.runs);
    const pipelinePhasesDir = join(blueprintDir, STATE_PATHS.pipeline.phases);
    const gapAnalysesDir = join(blueprintDir, STATE_PATHS.gaps.analyses);
    const gapReportsDir = join(blueprintDir, STATE_PATHS.gaps.reports);

    // 1. Archive completed/cancelled states
    archiveCompletedStates(pdcaCyclesDir, pdcaHistoryDir, [CYCLE_STATUS.COMPLETED, CYCLE_STATUS.CANCELLED]);
    archiveCompletedStates(pipelineRunsDir, pipelinePhasesDir, [RUN_STATUS.COMPLETED, RUN_STATUS.CANCELLED, RUN_STATUS.FAILED]);

    // 2. Remove all lock files
    removeAllLocks(pdcaCyclesDir);
    removeAllLocks(pipelineRunsDir);
    removeAllLocks(gapAnalysesDir);

    // 3. Clean up orphaned state files
    cleanOrphanedFiles(pdcaCyclesDir, pdcaHistoryDir);
    cleanOrphanedFiles(pipelineRunsDir, pipelinePhasesDir);
    cleanOrphanedFiles(gapAnalysesDir, gapReportsDir);

    // 4. Clean up temp files
    cleanTempFiles(pdcaCyclesDir);
    cleanTempFiles(pipelineRunsDir);
    cleanTempFiles(gapAnalysesDir);

    // 5. Clean recovery marker if it exists (session ended cleanly)
    const recoveryMarker = join(blueprintDir, '.recovery-marker');
    if (existsSync(recoveryMarker)) {
      try { unlinkSync(recoveryMarker); } catch { /* ignore */ }
    }

    process.stdout.write(JSON.stringify({ continue: true }));
  } catch (err) {
    error('session-cleanup', `Unexpected error: ${err?.message || err}`, { stack: err?.stack });
    process.stdout.write(JSON.stringify({ continue: true }));
  }
}

main();
