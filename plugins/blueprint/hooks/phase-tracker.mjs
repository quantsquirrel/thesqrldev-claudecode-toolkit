#!/usr/bin/env node

/**
 * Phase Tracker Hook (PostToolUse)
 * Tracks phase progression for active PDCA cycles and pipeline runs.
 * Only processes Task, Write, Edit, Bash tool calls; ignores the rest.
 *
 * Pattern: blueprint post-tool-verifier
 */

import { existsSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import {
  findBlueprintRoot,
  loadState,
  saveState,
  acquireLock,
  releaseLock
} from './lib/state-manager.mjs';
import { PDCA_PHASES, PIPELINE_PHASES, STATE_PATHS, CYCLE_STATUS, RUN_STATUS } from './lib/constants.mjs';
import { readStdin } from './lib/io.mjs';
import { error, info } from './lib/logger.mjs';

// Tools that indicate meaningful work progress
const TRACKED_TOOLS = new Set(['Task', 'Write', 'Edit', 'Bash']);

// Update activity timestamp on active PDCA cycles
function trackPdcaActivity(blueprintDir) {
  const cyclesDir = join(blueprintDir, STATE_PATHS.pdca.cycles);
  if (!existsSync(cyclesDir)) return;

  try {
    const files = readdirSync(cyclesDir).filter(f => f.endsWith('.json'));
    for (const file of files) {
      const filePath = join(cyclesDir, file);
      const lock = acquireLock(filePath, { timeoutMs: 1000 });
      try {
        const state = loadState(filePath);
        if (state && state.status === CYCLE_STATUS.ACTIVE) {
          state.updatedAt = new Date().toISOString();
          state.activityCount = (state.activityCount || 0) + 1;
          saveState(filePath, state);
        }
      } finally {
        if (lock) releaseLock(filePath);
      }
    }
  } catch {
    // Silently ignore errors
  }
}

// Update activity timestamp on active pipeline runs
function trackPipelineActivity(blueprintDir) {
  const runsDir = join(blueprintDir, STATE_PATHS.pipeline.runs);
  if (!existsSync(runsDir)) return;

  try {
    const files = readdirSync(runsDir).filter(f => f.endsWith('.json'));
    for (const file of files) {
      const filePath = join(runsDir, file);
      const lock = acquireLock(filePath, { timeoutMs: 1000 });
      try {
        const state = loadState(filePath);
        if (state && state.status === RUN_STATUS.RUNNING) {
          state.updatedAt = new Date().toISOString();
          state.activityCount = (state.activityCount || 0) + 1;
          saveState(filePath, state);
        }
      } finally {
        if (lock) releaseLock(filePath);
      }
    }
  } catch {
    // Silently ignore errors
  }
}

async function main() {
  info('phase-tracker', 'Hook started');
  try {
    const input = await readStdin();
    if (!input.trim()) {
      process.stdout.write(JSON.stringify({ continue: true }));
      return;
    }

    let data = {};
    try { data = JSON.parse(input); } catch { /* ignore */ }

    const toolName = data.tool_name || data.toolName || '';

    // Only track meaningful tool calls
    if (!TRACKED_TOOLS.has(toolName)) {
      process.stdout.write(JSON.stringify({ continue: true }));
      return;
    }

    // Find blueprint state directory
    let blueprintDir;
    try {
      blueprintDir = findBlueprintRoot(data.cwd || data.directory || process.cwd());
    } catch {
      process.stdout.write(JSON.stringify({ continue: true }));
      return;
    }

    // Track activity on active cycles and pipelines
    trackPdcaActivity(blueprintDir);
    trackPipelineActivity(blueprintDir);

    process.stdout.write(JSON.stringify({ continue: true }));
  } catch (err) {
    error('phase-tracker', `Unexpected error: ${err?.message || err}`, { stack: err?.stack });
    process.stdout.write(JSON.stringify({ continue: true }));
  }
}

main();
