#!/usr/bin/env node
/**
 * Session Restore Hook
 *
 * SessionStart hook that restores context after compaction or resume
 * by finding and scoring the best available context source.
 *
 * Source ranking (single best source, no multi-merge):
 *   1. Handoff .md files   (base score 1.0 - richest content)
 *   2. Pre-compact .json   (base score 0.8 - structured metadata)
 *   3. Draft .json          EXCLUDED (metadata only, per design decision)
 *
 * Score formula:
 *   score = baseScore × freshnessScore + relevanceBonus
 *
 * Works as a Claude Code SessionStart hook.
 */

import * as fs from 'fs';
import * as path from 'path';
import { tmpdir, homedir } from 'os';
import { execSync } from 'node:child_process';

import { createDebugLogger } from './utils.mjs';

const debugLog = createDebugLogger(
  'session-restore',
  path.join(tmpdir(), 'session-restore-debug.log'),
  'SESSION_RESTORE_DEBUG',
);

const SNAPSHOT_PREFIX = '.pre-compact-';
const MAX_AGE_MINUTES = 120; // Sources older than 2 hours score 0 freshness
const MAX_CONTEXT_CHARS = 8000; // Limit injected context size

/**
 * Get current git branch
 */
function getCurrentBranch() {
  try {
    return execSync('git rev-parse --abbrev-ref HEAD 2>/dev/null', {
      encoding: 'utf8',
      cwd: process.cwd(),
    }).trim();
  } catch (e) {
    return null;
  }
}

/**
 * Find handoff .md files
 */
function findHandoffFiles() {
  const sources = [];
  const handoffDir = path.join(process.cwd(), '.claude', 'handoffs');
  const globalHandoffDir = path.join(homedir(), '.claude', 'handoffs');

  for (const dir of [handoffDir, globalHandoffDir]) {
    try {
      if (!fs.existsSync(dir)) continue;
      const files = fs.readdirSync(dir);

      for (const file of files) {
        if (file.startsWith('handoff-') && file.endsWith('.md')) {
          const filePath = path.join(dir, file);
          const stat = fs.statSync(filePath);
          sources.push({
            type: 'handoff',
            path: filePath,
            name: file,
            mtime: stat.mtimeMs,
            baseScore: 1.0,
          });
        }
      }
    } catch (e) {
      debugLog('Error scanning handoff dir:', dir, e.message);
    }
  }

  return sources;
}

/**
 * Find pre-compact snapshot files
 */
function findSnapshotFiles() {
  const sources = [];
  const handoffDir = path.join(process.cwd(), '.claude', 'handoffs');

  try {
    if (!fs.existsSync(handoffDir)) return sources;
    const files = fs.readdirSync(handoffDir);

    for (const file of files) {
      if (file.startsWith(SNAPSHOT_PREFIX) && file.endsWith('.json')) {
        const filePath = path.join(handoffDir, file);
        const stat = fs.statSync(filePath);

        try {
          const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
          sources.push({
            type: 'snapshot',
            path: filePath,
            name: file,
            mtime: stat.mtimeMs,
            baseScore: 0.8,
            data,
          });
        } catch (e) {
          debugLog('Failed to parse snapshot:', file, e.message);
        }
      }
    }
  } catch (e) {
    debugLog('Error scanning snapshot dir:', e.message);
  }

  return sources;
}

/**
 * Calculate freshness score (0.0 - 1.0)
 * Files older than MAX_AGE_MINUTES get 0.
 */
function freshnessScore(mtimeMs) {
  const ageMinutes = (Date.now() - mtimeMs) / (60 * 1000);
  return Math.max(0, 1 - ageMinutes / MAX_AGE_MINUTES);
}

/**
 * Calculate relevance bonus (0.0 - 0.5)
 */
function relevanceBonus(source, sessionId, currentBranch) {
  let bonus = 0;

  // Same session ID: +0.3
  if (source.data?.sessionId === sessionId) {
    bonus += 0.3;
  } else if (source.type === 'handoff') {
    // For handoff files, check content for session ID
    try {
      const content = fs.readFileSync(source.path, 'utf8');
      if (content.includes(sessionId)) {
        bonus += 0.2;
      }
    } catch (e) {
      // Skip
    }
  }

  // Same git branch: +0.1
  if (currentBranch) {
    const sourceBranch = source.data?.gitBranch;
    if (sourceBranch === currentBranch) {
      bonus += 0.1;
    } else if (source.type === 'handoff') {
      try {
        const content = fs.readFileSync(source.path, 'utf8');
        if (content.includes(currentBranch)) {
          bonus += 0.05;
        }
      } catch (e) {
        // Skip
      }
    }
  }

  // Same working directory: +0.1
  if (source.data?.cwd === process.cwd()) {
    bonus += 0.1;
  }

  return bonus;
}

/**
 * Score a source
 */
function scoreSource(source, sessionId, currentBranch) {
  const freshness = freshnessScore(source.mtime);
  const relevance = relevanceBonus(source, sessionId, currentBranch);
  return source.baseScore * freshness + relevance;
}

/**
 * Format a pre-compact snapshot as readable context
 */
function formatSnapshot(data) {
  const lines = ['# Pre-Compact Snapshot', ''];

  if (data.timestamp) lines.push(`**Time:** ${data.timestamp}`);
  if (data.gitBranch) lines.push(`**Branch:** ${data.gitBranch}`);
  if (data.lastCommit) lines.push(`**Last Commit:** ${data.lastCommit}`);
  if (data.taskSize) lines.push(`**Task Size:** ${data.taskSize}`);
  if (data.estimatedTokens) {
    lines.push(`**Estimated Tokens:** ${data.estimatedTokens.toLocaleString()}`);
  }

  if (data.modifiedFiles?.length > 0) {
    lines.push('', '## Modified Files');
    for (const f of data.modifiedFiles.slice(0, 20)) {
      lines.push(`- ${f}`);
    }
    if (data.modifiedFiles.length > 20) {
      lines.push(`- ... and ${data.modifiedFiles.length - 20} more`);
    }
  }

  if (data.gitStatus) {
    lines.push('', '## Git Status', '```', data.gitStatus, '```');
  }

  return lines.join('\n');
}

/**
 * Read and truncate a handoff file
 */
function readHandoffContent(filePath) {
  try {
    let content = fs.readFileSync(filePath, 'utf8');
    if (content.length > MAX_CONTEXT_CHARS) {
      content = content.slice(0, MAX_CONTEXT_CHARS) + '\n\n... (truncated)';
    }
    return content;
  } catch (e) {
    debugLog('Failed to read handoff:', filePath, e.message);
    return null;
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

  debugLog('SessionStart triggered for session:', session_id);

  // Gather all available sources
  const handoffs = findHandoffFiles();
  const snapshots = findSnapshotFiles();
  const allSources = [...handoffs, ...snapshots];

  if (allSources.length === 0) {
    debugLog('No context sources found');
    return;
  }

  // Score and rank
  const currentBranch = getCurrentBranch();

  const scored = allSources.map(source => ({
    ...source,
    score: scoreSource(source, session_id, currentBranch),
  }));

  scored.sort((a, b) => b.score - a.score);

  const best = scored[0];
  debugLog('Best source:', best.name, 'score:', best.score.toFixed(3));

  // Skip if score is too low (stale/irrelevant)
  if (best.score < 0.1) {
    debugLog('Best source score too low, skipping restore');
    return;
  }

  // Extract content from best source
  let restoredContext;

  if (best.type === 'handoff') {
    restoredContext = readHandoffContent(best.path);
  } else if (best.type === 'snapshot') {
    restoredContext = formatSnapshot(best.data);
  }

  if (!restoredContext) return;

  // Wrap with header
  const header = `📋 **Session Context Restored** (source: ${best.name}, score: ${best.score.toFixed(2)})\n\n`;
  const context = header + restoredContext;

  const result = {
    decision: 'approve',
    additionalContext: context,
  };

  console.log(JSON.stringify(result));
}

main();
