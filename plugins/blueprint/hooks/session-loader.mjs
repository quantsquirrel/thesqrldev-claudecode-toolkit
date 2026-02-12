#!/usr/bin/env node

/**
 * Session Loader Hook (SessionStart)
 * Loads active cycles/pipelines, checks agent availability,
 * cleans up orphaned state from previous sessions.
 *
 * Pattern: blueprint session-start
 */

import { existsSync, readdirSync, unlinkSync, statSync } from 'node:fs';
import { join } from 'node:path';
import {
  findBlueprintRoot,
  loadState,
  saveState,
  listActiveItems,
  archiveState,
  checkStaleness,
  ensureDir
} from './lib/state-manager.mjs';
import { STATE_PATHS, CYCLE_STATUS, RUN_STATUS, PDCA_PHASES, PIPELINE_PHASES } from './lib/constants.mjs';
import { readStdin } from './lib/io.mjs';
import { error, info } from './lib/logger.mjs';

// Max age for orphaned state: 24 hours
const ORPHAN_MAX_AGE_MS = 24 * 60 * 60 * 1000;
// Max age for stale locks: 5 minutes
const STALE_LOCK_AGE_MS = 5 * 60 * 1000;

// Clean up stale .lock files in a directory
function cleanStaleLocks(dirPath) {
  if (!existsSync(dirPath)) return;
  try {
    const files = readdirSync(dirPath).filter(f => f.endsWith('.lock'));
    const now = Date.now();
    for (const file of files) {
      const lockPath = join(dirPath, file);
      try {
        const stat = statSync(lockPath);
        if (now - stat.mtimeMs > STALE_LOCK_AGE_MS) {
          unlinkSync(lockPath);
        }
      } catch { /* ignore */ }
    }
  } catch { /* ignore */ }
}

// Clean up orphaned state files (too old, no active session)
function cleanOrphanedStates(dirPath, historyDir) {
  if (!existsSync(dirPath)) return;
  try {
    const files = readdirSync(dirPath).filter(f => f.endsWith('.json'));
    for (const file of files) {
      const filePath = join(dirPath, file);
      const state = loadState(filePath);
      if (state && checkStaleness(state, ORPHAN_MAX_AGE_MS)) {
        // Archive stale state instead of deleting
        archiveState(filePath, historyDir);
      }
    }
  } catch { /* ignore */ }
}

// Check for recovery marker from compact-preserver
function checkRecoveryMarker(blueprintDir) {
  const markerPath = join(blueprintDir, '.recovery-marker');
  if (!existsSync(markerPath)) return null;

  const marker = loadState(markerPath);
  if (marker) {
    // Clean up the marker after reading
    try { unlinkSync(markerPath); } catch { /* ignore */ }
  }
  return marker;
}

// Check agent availability
function checkAgentAvailability() {
  return process.env.BLUEPRINT_AGENTS_AVAILABLE === 'true' ||
         process.env.BLUEPRINT_AGENTS_AVAILABLE === '1';
}

// Summarize active PDCA cycles
function summarizePdcaCycles(blueprintDir) {
  const activeCyclesPath = join(blueprintDir, STATE_PATHS.pdca.activeCycles);
  const activeItems = listActiveItems(activeCyclesPath);
  if (!activeItems.items || activeItems.items.length === 0) return null;

  const summaries = [];
  for (const item of activeItems.items) {
    const cyclePath = join(blueprintDir, STATE_PATHS.pdca.cycles, `${item.id}.json`);
    const cycle = loadState(cyclePath);
    if (cycle && cycle.status === CYCLE_STATUS.ACTIVE) {
      const phaseIndex = PDCA_PHASES.indexOf(cycle.currentPhase || 'plan');
      summaries.push(`  - Cycle ${item.id}: phase=${cycle.currentPhase || 'plan'} (${phaseIndex + 1}/${PDCA_PHASES.length}), objective="${cycle.objective || 'N/A'}"`);
    }
  }
  return summaries.length > 0 ? summaries : null;
}

// Summarize active pipeline runs
function summarizePipelineRuns(blueprintDir) {
  const runsDir = join(blueprintDir, STATE_PATHS.pipeline.runs);
  if (!existsSync(runsDir)) return null;

  const summaries = [];
  try {
    const files = readdirSync(runsDir).filter(f => f.endsWith('.json'));
    for (const file of files) {
      const run = loadState(join(runsDir, file));
      if (run && run.status === RUN_STATUS.RUNNING) {
        const currentPhase = run.currentPhase || PIPELINE_PHASES[0];
        const phaseIndex = PIPELINE_PHASES.indexOf(currentPhase);
        const totalPhases = run.preset ? `${run.activePhases?.length || '?'}` : String(PIPELINE_PHASES.length);
        summaries.push(`  - Run ${run.id || file.replace('.json', '')}: phase=${currentPhase} (${phaseIndex + 1}/${totalPhases}), preset=${run.preset || 'full'}`);
      }
    }
  } catch { /* ignore */ }
  return summaries.length > 0 ? summaries : null;
}

// Summarize active gap analyses
function summarizeGapAnalyses(blueprintDir) {
  const analysesDir = join(blueprintDir, STATE_PATHS.gaps.analyses);
  if (!existsSync(analysesDir)) return null;

  const summaries = [];
  try {
    const files = readdirSync(analysesDir).filter(f => f.endsWith('.json'));
    for (const file of files) {
      const analysis = loadState(join(analysesDir, file));
      if (analysis && analysis.status === 'active') {
        summaries.push(`  - Analysis ${analysis.id || file.replace('.json', '')}: gaps=${analysis.gapCount || 0}, target="${analysis.target || 'N/A'}"`);
      }
    }
  } catch { /* ignore */ }
  return summaries.length > 0 ? summaries : null;
}

async function main() {
  info('session-loader', 'Hook started');
  try {
    const input = await readStdin();
    let data = {};
    try { data = JSON.parse(input); } catch { /* ignore */ }

    const directory = data.cwd || data.directory || process.cwd();
    const messages = [];

    let blueprintDir;
    try {
      blueprintDir = findBlueprintRoot(directory);
    } catch {
      process.stdout.write(JSON.stringify({ continue: true }));
      return;
    }

    // Check recovery marker from previous compaction
    const recoveryMarker = checkRecoveryMarker(blueprintDir);
    if (recoveryMarker) {
      messages.push(`[BLUEPRINT RECOVERY] Recovered state from previous compaction at ${recoveryMarker.timestamp || 'unknown time'}.`);
    }

    // Clean up stale locks
    cleanStaleLocks(join(blueprintDir, STATE_PATHS.pdca.cycles));
    cleanStaleLocks(join(blueprintDir, STATE_PATHS.pipeline.runs));
    cleanStaleLocks(join(blueprintDir, STATE_PATHS.gaps.analyses));

    // Clean up orphaned states
    cleanOrphanedStates(
      join(blueprintDir, STATE_PATHS.pdca.cycles),
      join(blueprintDir, STATE_PATHS.pdca.history)
    );
    cleanOrphanedStates(
      join(blueprintDir, STATE_PATHS.pipeline.runs),
      join(blueprintDir, STATE_PATHS.pipeline.phases)
    );

    // Summarize active states
    const pdcaSummaries = summarizePdcaCycles(blueprintDir);
    const pipelineSummaries = summarizePipelineRuns(blueprintDir);
    const gapSummaries = summarizeGapAnalyses(blueprintDir);

    const hasActive = pdcaSummaries || pipelineSummaries || gapSummaries;

    if (hasActive) {
      let summary = '[BLUEPRINT ACTIVE STATE]\n\n';

      if (pdcaSummaries) {
        summary += 'Active PDCA Cycles:\n' + pdcaSummaries.join('\n') + '\n\n';
      }
      if (pipelineSummaries) {
        summary += 'Active Pipeline Runs:\n' + pipelineSummaries.join('\n') + '\n\n';
      }
      if (gapSummaries) {
        summary += 'Active Gap Analyses:\n' + gapSummaries.join('\n') + '\n\n';
      }

      // Agent availability
      const agentsAvailable = checkAgentAvailability();
      summary += `Agent availability: ${agentsAvailable ? 'AVAILABLE' : 'NOT CONFIGURED (set BLUEPRINT_AGENTS_AVAILABLE=true)'}\n`;
      summary += '\nUse /blueprint:cancel to cancel any active mode.';

      messages.push(summary);
    }

    if (messages.length > 0) {
      process.stdout.write(JSON.stringify({
        continue: true,
        hookSpecificOutput: {
          hookEventName: 'SessionStart',
          additionalContext: messages.join('\n\n---\n\n')
        }
      }));
    } else {
      process.stdout.write(JSON.stringify({ continue: true }));
    }
  } catch (err) {
    error('session-loader', `Unexpected error: ${err?.message || err}`, { stack: err?.stack });
    process.stdout.write(JSON.stringify({ continue: true }));
  }
}

main();
