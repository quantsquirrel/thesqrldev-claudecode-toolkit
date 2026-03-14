/**
 * Handoff Diff Module
 *
 * Compares two handoff files section-by-section and produces an
 * incremental diff.  Useful when handoffs are created repeatedly —
 * shows only what changed between the previous and current handoff.
 *
 * All public functions are pure (no I/O) except findRecentHandoffs
 * which reads the filesystem.
 */

import * as fs from 'fs';
import * as path from 'path';

// ── Filesystem helpers ─────────────────────────────────────────────

/**
 * Return the most recent N handoff file paths from a directory,
 * sorted newest-first by the timestamp embedded in the filename.
 *
 * Filenames are expected to match `handoff-YYYYMMDD-HHMMSS*.md`
 * or the level-prefixed variants `l[123]-*.md`.
 *
 * @param {string} handoffDir - Absolute path to the handoffs directory
 * @param {number} [count=2]  - How many files to return
 * @returns {string[]} Absolute paths, newest first
 */
export function findRecentHandoffs(handoffDir, count = 2) {
  try {
    if (!fs.existsSync(handoffDir)) return [];

    const files = fs.readdirSync(handoffDir)
      .filter(f => /^(handoff|l[123])-.*\.md$/.test(f));

    // Sort by filename descending (timestamp is lexicographically sortable)
    files.sort((a, b) => b.localeCompare(a));

    return files.slice(0, count).map(f => path.join(handoffDir, f));
  } catch {
    return [];
  }
}

// ── Section parser ─────────────────────────────────────────────────

/**
 * Parse a handoff markdown string into a Map of section-name → content.
 *
 * Sections are delimited by `## <Name>` headings.  The preamble before
 * the first `##` heading (metadata lines like Time, Topic, etc.) is
 * stored under the key `"_preamble"`.
 *
 * @param {string} content - Raw markdown text of a handoff file
 * @returns {Map<string, string>} Section name → trimmed body text
 */
export function parseHandoffSections(content) {
  const sections = new Map();
  const lines = content.split('\n');

  let currentSection = '_preamble';
  let buffer = [];

  for (const line of lines) {
    const heading = line.match(/^## (.+)$/);
    if (heading) {
      // Flush previous section
      sections.set(currentSection, buffer.join('\n').trim());
      currentSection = heading[1].trim();
      buffer = [];
    } else {
      buffer.push(line);
    }
  }

  // Flush last section
  sections.set(currentSection, buffer.join('\n').trim());

  return sections;
}

// ── List-item helpers ──────────────────────────────────────────────

/**
 * Extract list items (lines starting with `- `) from a section body.
 * Checkbox markers like `[x]` and `[ ]` are preserved.
 *
 * @param {string} body - Section body text
 * @returns {string[]} Individual list items, trimmed
 */
function extractListItems(body) {
  return body
    .split('\n')
    .filter(l => /^\s*- /.test(l))
    .map(l => l.replace(/^\s*- /, '').trim());
}

/**
 * Sections whose content is best compared as a set of list items
 * rather than as a single blob of text.
 */
const LIST_SECTIONS = new Set([
  'Completed',
  'Pending',
  'Key Decisions',
  'Failed Approaches',
  'Files Modified',
  'Constraints',
  'User Requests',
]);

// ── Diff engine ────────────────────────────────────────────────────

/**
 * Compute a section-by-section diff between two parsed handoffs.
 *
 * For list-oriented sections (Completed, Pending, …) the diff is
 * item-level (added / removed).  For prose sections (Summary, Next
 * Step, …) the diff reports the full text change.
 *
 * @param {Map<string, string>} previous - Parsed sections of the older handoff
 * @param {Map<string, string>} current  - Parsed sections of the newer handoff
 * @returns {{
 *   added:     Record<string, string[]>,
 *   removed:   Record<string, string[]>,
 *   changed:   Record<string, { from: string, to: string }>,
 *   unchanged: string[],
 * }}
 */
export function diffHandoffs(previous, current) {
  const added = {};
  const removed = {};
  const changed = {};
  const unchanged = [];

  // Collect every section name from both sides
  const allSections = new Set([...previous.keys(), ...current.keys()]);
  // Skip preamble — metadata always differs (timestamp, topic)
  allSections.delete('_preamble');

  for (const name of allSections) {
    const prev = previous.get(name) ?? '';
    const curr = current.get(name) ?? '';

    // Entirely new section in current
    if (!previous.has(name)) {
      if (LIST_SECTIONS.has(name)) {
        added[name] = extractListItems(curr);
      } else {
        changed[name] = { from: '', to: curr };
      }
      continue;
    }

    // Section removed in current
    if (!current.has(name)) {
      if (LIST_SECTIONS.has(name)) {
        removed[name] = extractListItems(prev);
      } else {
        changed[name] = { from: prev, to: '' };
      }
      continue;
    }

    // Both sides exist — compare
    if (prev === curr) {
      unchanged.push(name);
      continue;
    }

    if (LIST_SECTIONS.has(name)) {
      const prevItems = extractListItems(prev);
      const currItems = extractListItems(curr);
      const prevSet = new Set(prevItems);
      const currSet = new Set(currItems);

      const addedItems = currItems.filter(i => !prevSet.has(i));
      const removedItems = prevItems.filter(i => !currSet.has(i));

      if (addedItems.length > 0) added[name] = addedItems;
      if (removedItems.length > 0) removed[name] = removedItems;
      if (addedItems.length === 0 && removedItems.length === 0) {
        unchanged.push(name);
      }
    } else {
      changed[name] = { from: prev, to: curr };
    }
  }

  return { added, removed, changed, unchanged };
}

// ── Formatter ──────────────────────────────────────────────────────

/**
 * Render a diff result as human-readable markdown.
 *
 * Conventions:
 *   `+` added item/section
 *   `-` removed item/section
 *   `~` changed (prose) section
 *
 * @param {{ added, removed, changed, unchanged }} diff
 * @returns {string} Formatted markdown string
 */
export function formatDiff(diff) {
  const { added, removed, changed, unchanged } = diff;

  const hasChanges =
    Object.keys(added).length > 0 ||
    Object.keys(removed).length > 0 ||
    Object.keys(changed).length > 0;

  if (!hasChanges) {
    return '# Handoff Diff\n\nNo changes detected between the two handoffs.';
  }

  const lines = ['# Handoff Diff', ''];

  // Added items per section
  for (const [section, items] of Object.entries(added)) {
    lines.push(`## ${section}`);
    for (const item of items) {
      lines.push(`+ ${item}`);
    }
    lines.push('');
  }

  // Removed items per section
  for (const [section, items] of Object.entries(removed)) {
    lines.push(`## ${section}`);
    for (const item of items) {
      lines.push(`- ${item}`);
    }
    lines.push('');
  }

  // Changed prose sections
  for (const [section, { from, to }] of Object.entries(changed)) {
    lines.push(`## ${section}`);
    if (from) {
      lines.push(`- ${from}`);
    }
    if (to) {
      lines.push(`+ ${to}`);
    }
    lines.push('');
  }

  // Unchanged sections (summary line)
  if (unchanged.length > 0) {
    lines.push(`**Unchanged sections:** ${unchanged.join(', ')}`);
    lines.push('');
  }

  return lines.join('\n').trimEnd();
}
