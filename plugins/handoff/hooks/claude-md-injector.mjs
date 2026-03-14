/**
 * CLAUDE.md Injector
 *
 * Injects a compact summary of the most recent handoff into the project's
 * CLAUDE.md file using marker-based sections. This allows new sessions to
 * pick up basic context automatically without manual clipboard paste.
 *
 * The injected content is kept under ~200 tokens (Topic + status counts +
 * Next Step + file pointer) to stay well within CLAUDE.md's 3,000-token
 * recommended budget.
 *
 * Marker pair: <!-- HANDOFF:START --> ... <!-- HANDOFF:END -->
 * If markers exist, content is replaced. Otherwise appended to file end.
 * If CLAUDE.md does not exist, nothing is created (warning only).
 */

import * as fs from 'fs';
import * as path from 'path';
import { tmpdir } from 'os';

import { createDebugLogger } from './utils.mjs';

const debugLog = createDebugLogger(
  'claude-md-injector',
  path.join(tmpdir(), 'claude-md-injector-debug.log'),
  'CLAUDE_MD_INJECTOR_DEBUG',
);

const MARKER_START = '<!-- HANDOFF:START -->';
const MARKER_END = '<!-- HANDOFF:END -->';

/**
 * Find the most recent handoff file in the project's .claude/handoffs/ directory.
 *
 * @param {string} projectRoot - Absolute path to the project root
 * @returns {string|null} Path to the newest handoff file, or null
 */
function findLatestHandoff(projectRoot) {
  const handoffDir = path.join(projectRoot, '.claude', 'handoffs');

  try {
    if (!fs.existsSync(handoffDir)) {
      debugLog('Handoff directory not found:', handoffDir);
      return null;
    }

    const files = fs.readdirSync(handoffDir);
    let latest = null;
    let latestMtime = 0;

    for (const file of files) {
      if (!/^(handoff|l[123])-.*\.md$/.test(file)) continue;

      const filePath = path.join(handoffDir, file);
      try {
        const stat = fs.statSync(filePath);
        if (stat.mtimeMs > latestMtime) {
          latestMtime = stat.mtimeMs;
          latest = filePath;
        }
      } catch (e) {
        debugLog('Failed to stat file:', file, e.message);
      }
    }

    return latest;
  } catch (e) {
    debugLog('Error scanning handoff dir:', e.message);
    return null;
  }
}

/**
 * Extract a compact summary from handoff markdown content.
 *
 * Pulls Topic, counts of completed/pending items, and Next Step.
 *
 * @param {string} content - Raw handoff markdown
 * @returns {{ topic: string, completed: number, pending: number, nextStep: string } | null}
 */
function extractSummary(content) {
  // Extract Topic from **Topic:** line
  const topicMatch = content.match(/\*\*Topic:\*\*\s*(.+)/);
  const topic = topicMatch ? topicMatch[1].trim() : null;

  if (!topic) {
    debugLog('No topic found in handoff content');
    return null;
  }

  // Count completed items: lines matching "- [x]"
  const completedMatches = content.match(/^- \[x\]/gm);
  const completed = completedMatches ? completedMatches.length : 0;

  // Count pending items: lines matching "- [ ]"
  const pendingMatches = content.match(/^- \[ \]/gm);
  const pending = pendingMatches ? pendingMatches.length : 0;

  // Extract Next Step section content (everything after ## Next Step until next ## or EOF)
  let nextStep = '';
  const nextStepMatch = content.match(/## Next Step\n([\s\S]*?)(?=\n## |\n<!-- |$)/);
  if (nextStepMatch) {
    // Take only the first sentence/line, trimmed
    const raw = nextStepMatch[1].trim();
    const firstLine = raw.split('\n')[0].trim();
    // Truncate to ~120 chars to keep token budget low
    nextStep = firstLine.length > 120 ? firstLine.slice(0, 117) + '...' : firstLine;
  }

  return { topic, completed, pending, nextStep };
}

/**
 * Build the marker-wrapped section to inject into CLAUDE.md.
 *
 * @param {{ topic: string, completed: number, pending: number, nextStep: string }} summary
 * @param {string} handoffRelPath - Relative path to the handoff file
 * @returns {string}
 */
function buildSection(summary, handoffRelPath) {
  const lines = [
    MARKER_START,
    '## Last Session Context',
    `**Topic:** ${summary.topic}`,
    `**Status:** ${summary.completed} completed, ${summary.pending} pending`,
  ];

  if (summary.nextStep) {
    lines.push(`**Next:** ${summary.nextStep}`);
  }

  lines.push(`**Full handoff:** ${handoffRelPath}`);
  lines.push(MARKER_END);

  return lines.join('\n');
}

/**
 * Inject the most recent handoff summary into a project's CLAUDE.md.
 *
 * If CLAUDE.md does not exist, logs a warning and returns without creating it.
 * If the HANDOFF markers already exist, replaces the content between them.
 * Otherwise appends the section to the end of the file.
 *
 * @param {string} handoffPath - Absolute path to the handoff .md file
 * @param {string} projectRoot - Absolute path to the project root
 * @returns {{ success: boolean, message: string }}
 */
export function injectToClaudeMd(handoffPath, projectRoot) {
  try {
    const claudeMdPath = path.join(projectRoot, 'CLAUDE.md');

    // CLAUDE.md must already exist
    if (!fs.existsSync(claudeMdPath)) {
      const msg = 'CLAUDE.md not found, skipping injection';
      debugLog(msg);
      return { success: false, message: msg };
    }

    // Read handoff content
    let handoffContent;
    try {
      handoffContent = fs.readFileSync(handoffPath, 'utf8');
    } catch (e) {
      const msg = `Failed to read handoff file: ${e.message}`;
      debugLog(msg);
      return { success: false, message: msg };
    }

    // Extract summary
    const summary = extractSummary(handoffContent);
    if (!summary) {
      const msg = 'Could not extract summary from handoff';
      debugLog(msg);
      return { success: false, message: msg };
    }

    // Build relative path for the pointer
    const handoffRelPath = path.relative(projectRoot, handoffPath);

    // Build the section
    const section = buildSection(summary, handoffRelPath);

    // Read existing CLAUDE.md
    let claudeMd = fs.readFileSync(claudeMdPath, 'utf8');

    // Replace or append
    const startIdx = claudeMd.indexOf(MARKER_START);
    const endIdx = claudeMd.indexOf(MARKER_END);

    if (startIdx !== -1 && endIdx !== -1) {
      // Replace existing section
      claudeMd =
        claudeMd.slice(0, startIdx) +
        section +
        claudeMd.slice(endIdx + MARKER_END.length);
    } else {
      // Append to end with separator
      const separator = claudeMd.endsWith('\n') ? '\n' : '\n\n';
      claudeMd += separator + section + '\n';
    }

    fs.writeFileSync(claudeMdPath, claudeMd);

    const msg = `Injected handoff summary (topic: ${summary.topic})`;
    debugLog(msg);
    return { success: true, message: msg };
  } catch (e) {
    const msg = `Injection failed: ${e.message}`;
    debugLog(msg);
    return { success: false, message: msg };
  }
}

/**
 * CLI entry point: find the latest handoff and inject into CLAUDE.md.
 * Can be called directly: node claude-md-injector.mjs [projectRoot]
 */
function main() {
  const projectRoot = process.argv[2] || process.cwd();

  // Find handoff path from argument or locate the latest one
  const handoffPath = process.argv[3] || findLatestHandoff(projectRoot);

  if (!handoffPath) {
    debugLog('No handoff files found');
    return;
  }

  const result = injectToClaudeMd(handoffPath, projectRoot);
  debugLog('Result:', result);
}

// Run main() only when executed directly (not imported)
const isDirectRun =
  process.argv[1] &&
  path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname);

if (isDirectRun) {
  main();
}
