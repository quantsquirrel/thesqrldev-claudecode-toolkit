/**
 * Compression Stats Module
 *
 * Calculates and tracks compression ratios when generating handoff documents.
 * Compares original session token count against handoff token count to show
 * how much context was distilled.
 *
 * Persists history to .claude/handoffs/stats.json for trend analysis.
 */

import * as fs from 'fs';
import * as path from 'path';
import { estimateTokens, getSharedTokenCount, loadJsonState, saveJsonState } from './utils.mjs';

const STATS_FILE = 'stats.json';

/**
 * Calculate compression statistics for a handoff.
 *
 * @param {string} sessionId - Session identifier used in shared token state
 * @param {string} handoffPath - Absolute path to the generated handoff file
 * @returns {{ sessionTokens: number, handoffTokens: number, compressionRatio: number, savings: string } | null}
 *   Compression stats object, or null if session tokens are unavailable
 */
export function calculateCompressionStats(sessionId, handoffPath) {
  const sessionTokens = getSharedTokenCount(sessionId);
  if (!sessionTokens || sessionTokens <= 0) {
    return null;
  }

  let handoffContent;
  try {
    handoffContent = fs.readFileSync(handoffPath, 'utf8');
  } catch {
    return null;
  }

  const handoffTokens = estimateTokens(handoffContent);
  if (handoffTokens <= 0) {
    return null;
  }

  const compressionRatio = Math.round(sessionTokens / handoffTokens);
  const savingsPercent = ((1 - handoffTokens / sessionTokens) * 100).toFixed(1);

  return {
    sessionTokens,
    handoffTokens,
    compressionRatio,
    savings: `${savingsPercent}% saved`,
  };
}

/**
 * Append compression stats to the persistent history file.
 *
 * @param {object} stats - Stats object from calculateCompressionStats
 * @param {string} stats.sessionTokens - Original session token count
 * @param {string} stats.handoffTokens - Handoff document token count
 * @param {string} stats.compressionRatio - Compression ratio
 * @param {string} stats.savings - Human-readable savings string
 * @param {string} projectRoot - Project root directory (contains .claude/)
 */
export function saveStats(stats, projectRoot) {
  const statsPath = path.join(projectRoot, '.claude', 'handoffs', STATS_FILE);
  const statsDir = path.dirname(statsPath);

  try {
    fs.mkdirSync(statsDir, { recursive: true });
  } catch {
    // Directory already exists
  }

  const history = loadJsonState(statsPath, []);
  history.push({
    ...stats,
    timestamp: new Date().toISOString(),
  });

  saveJsonState(statsPath, history);
}

/**
 * Retrieve historical compression statistics with aggregates.
 *
 * @param {string} projectRoot - Project root directory (contains .claude/)
 * @returns {{ entries: object[], avg: number, max: number, min: number, count: number }}
 *   Historical stats with average, max, and min compression ratios
 */
export function getHistoricalStats(projectRoot) {
  const statsPath = path.join(projectRoot, '.claude', 'handoffs', STATS_FILE);
  const entries = loadJsonState(statsPath, []);

  if (!Array.isArray(entries) || entries.length === 0) {
    return { entries: [], avg: 0, max: 0, min: 0, count: 0 };
  }

  const ratios = entries.map((e) => e.compressionRatio).filter((r) => r > 0);
  if (ratios.length === 0) {
    return { entries, avg: 0, max: 0, min: 0, count: entries.length };
  }

  const sum = ratios.reduce((a, b) => a + b, 0);

  return {
    entries,
    avg: Math.round(sum / ratios.length),
    max: Math.max(...ratios),
    min: Math.min(...ratios),
    count: entries.length,
  };
}

/**
 * Format compression stats into a human-readable display string.
 *
 * @param {object} stats - Stats object from calculateCompressionStats
 * @returns {string} Formatted display string
 */
export function formatStatsDisplay(stats) {
  if (!stats) {
    return 'Compression stats unavailable (no session token data).';
  }

  const sessionStr = stats.sessionTokens.toLocaleString();
  const handoffStr = stats.handoffTokens.toLocaleString();

  return `Compression: ${sessionStr} -> ${handoffStr} tokens (${stats.compressionRatio}x, ${stats.savings})`;
}
