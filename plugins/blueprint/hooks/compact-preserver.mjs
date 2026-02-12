#!/usr/bin/env node

/**
 * Compact Preserver Hook (PreCompact)
 * Preserves active blueprint state before context compaction.
 * Creates a recovery marker so session-loader can restore on next SessionStart.
 *
 * Pattern: blueprint pre-compact
 */

import { existsSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import {
  findBlueprintRoot,
  loadState,
  saveState,
  ensureDir,
  listActiveItems
} from './lib/state-manager.mjs';
import { STATE_PATHS, CYCLE_STATUS, RUN_STATUS } from './lib/constants.mjs';
import { readStdin } from './lib/io.mjs';
import { error, info } from './lib/logger.mjs';

// Collect active PDCA cycle summaries for preservation
function collectActivePdca(blueprintDir) {
  const activeCyclesPath = join(blueprintDir, STATE_PATHS.pdca.activeCycles);
  const activeItems = listActiveItems(activeCyclesPath);
  if (!activeItems.items || activeItems.items.length === 0) return [];

  const results = [];
  for (const item of activeItems.items) {
    const cyclePath = join(blueprintDir, STATE_PATHS.pdca.cycles, `${item.id}.json`);
    const cycle = loadState(cyclePath);
    if (cycle && cycle.status === CYCLE_STATUS.ACTIVE) {
      results.push({
        type: 'pdca',
        id: item.id,
        phase: cycle.currentPhase || 'plan',
        objective: cycle.objective || '',
        updatedAt: cycle.updatedAt || cycle.createdAt
      });
    }
  }
  return results;
}

// Collect active pipeline run summaries for preservation
function collectActivePipelines(blueprintDir) {
  const runsDir = join(blueprintDir, STATE_PATHS.pipeline.runs);
  if (!existsSync(runsDir)) return [];

  const results = [];
  try {
    const files = readdirSync(runsDir).filter(f => f.endsWith('.json'));
    for (const file of files) {
      const run = loadState(join(runsDir, file));
      if (run && run.status === RUN_STATUS.RUNNING) {
        results.push({
          type: 'pipeline',
          id: run.id || file.replace('.json', ''),
          phase: run.currentPhase || 'requirements',
          preset: run.preset || 'full',
          updatedAt: run.updatedAt || run.createdAt
        });
      }
    }
  } catch { /* ignore */ }
  return results;
}

// Collect active gap analysis summaries
function collectActiveGaps(blueprintDir) {
  const analysesDir = join(blueprintDir, STATE_PATHS.gaps.analyses);
  if (!existsSync(analysesDir)) return [];

  const results = [];
  try {
    const files = readdirSync(analysesDir).filter(f => f.endsWith('.json'));
    for (const file of files) {
      const analysis = loadState(join(analysesDir, file));
      if (analysis && analysis.status === 'active') {
        results.push({
          type: 'gap',
          id: analysis.id || file.replace('.json', ''),
          target: analysis.target || '',
          gapCount: analysis.gapCount || 0,
          updatedAt: analysis.updatedAt || analysis.createdAt
        });
      }
    }
  } catch { /* ignore */ }
  return results;
}

async function main() {
  info('compact-preserver', 'Hook started');
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

    // Collect all active states
    const activePdca = collectActivePdca(blueprintDir);
    const activePipelines = collectActivePipelines(blueprintDir);
    const activeGaps = collectActiveGaps(blueprintDir);
    const allActive = [...activePdca, ...activePipelines, ...activeGaps];

    if (allActive.length === 0) {
      process.stdout.write(JSON.stringify({ continue: true }));
      return;
    }

    // Create recovery marker with active state summaries
    const recoveryMarker = {
      timestamp: new Date().toISOString(),
      activeStates: allActive,
      reason: 'pre-compact preservation'
    };

    try {
      saveState(join(blueprintDir, '.recovery-marker'), recoveryMarker);
    } catch {
      // If save fails, still allow compaction to proceed
    }

    // Build additionalContext so the compacted context retains awareness
    const lines = ['[BLUEPRINT STATE PRESERVED FOR COMPACTION]', ''];
    for (const item of allActive) {
      if (item.type === 'pdca') {
        lines.push(`- PDCA cycle ${item.id}: phase=${item.phase}, objective="${item.objective}"`);
      } else if (item.type === 'pipeline') {
        lines.push(`- Pipeline run ${item.id}: phase=${item.phase}, preset=${item.preset}`);
      } else if (item.type === 'gap') {
        lines.push(`- Gap analysis ${item.id}: target="${item.target}", gaps=${item.gapCount}`);
      }
    }
    lines.push('', 'These states have been preserved and will be restored after compaction.');

    process.stdout.write(JSON.stringify({
      continue: true,
      hookSpecificOutput: {
        hookEventName: 'PreCompact',
        additionalContext: lines.join('\n')
      }
    }));
  } catch (err) {
    error('compact-preserver', `Unexpected error: ${err?.message || err}`, { stack: err?.stack });
    process.stdout.write(JSON.stringify({ continue: true }));
  }
}

main();
