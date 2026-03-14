/**
 * Phase 2 Module Tests
 *
 * Covers:
 *   - claude-md-injector.mjs: injectToClaudeMd
 *   - compression-stats.mjs: calculateCompressionStats, formatStatsDisplay
 *   - handoff-diff.mjs: parseHandoffSections, diffHandoffs, formatDiff
 *   - handoffignore.mjs: loadIgnorePatterns, shouldIgnore, filterFiles
 */

import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'fs';
import * as path from 'path';
import { tmpdir } from 'os';
import * as crypto from 'crypto';

import { injectToClaudeMd } from '../claude-md-injector.mjs';
import { formatStatsDisplay } from '../compression-stats.mjs';
import {
  parseHandoffSections,
  diffHandoffs,
  formatDiff,
  findRecentHandoffs,
} from '../handoff-diff.mjs';
import {
  loadIgnorePatterns,
  shouldIgnore,
  filterFiles,
} from '../handoffignore.mjs';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Generate a unique temp directory to isolate each test */
function makeTempDir(prefix = 'phase2-test-') {
  return fs.mkdtempSync(path.join(tmpdir(), prefix));
}

/** Cleanup helper */
function rmrf(dirPath) {
  try {
    fs.rmSync(dirPath, { recursive: true, force: true });
  } catch {
    // best-effort cleanup
  }
}

// ---------------------------------------------------------------------------
// injectToClaudeMd
// ---------------------------------------------------------------------------

describe('injectToClaudeMd', () => {
  let projectRoot;

  beforeEach(() => {
    projectRoot = makeTempDir('inject-');
  });

  afterEach(() => {
    rmrf(projectRoot);
  });

  it('returns failure when CLAUDE.md does not exist', () => {
    const handoffPath = path.join(projectRoot, 'handoff.md');
    fs.writeFileSync(handoffPath, '**Topic:** Test topic\n## Next Step\nDo something');

    const result = injectToClaudeMd(handoffPath, projectRoot);

    assert.equal(result.success, false);
    assert.match(result.message, /CLAUDE\.md not found/);
  });

  it('returns failure when handoff file cannot be read', () => {
    fs.writeFileSync(path.join(projectRoot, 'CLAUDE.md'), '# Project\n');
    const bogusPath = path.join(projectRoot, 'nonexistent.md');

    const result = injectToClaudeMd(bogusPath, projectRoot);

    assert.equal(result.success, false);
    assert.match(result.message, /Failed to read handoff file/);
  });

  it('returns failure when handoff has no Topic line', () => {
    fs.writeFileSync(path.join(projectRoot, 'CLAUDE.md'), '# Project\n');
    const handoffPath = path.join(projectRoot, 'handoff.md');
    fs.writeFileSync(handoffPath, 'No topic here\n## Next Step\nDo something');

    const result = injectToClaudeMd(handoffPath, projectRoot);

    assert.equal(result.success, false);
    assert.match(result.message, /Could not extract summary/);
  });

  it('appends handoff summary to CLAUDE.md when no markers exist', () => {
    const claudeMdPath = path.join(projectRoot, 'CLAUDE.md');
    fs.writeFileSync(claudeMdPath, '# My Project\n');

    const handoffPath = path.join(projectRoot, 'handoff.md');
    fs.writeFileSync(
      handoffPath,
      [
        '**Topic:** Implement auth module',
        '- [x] Create login endpoint',
        '- [x] Add JWT validation',
        '- [ ] Write tests',
        '## Next Step',
        'Write integration tests for the auth flow',
      ].join('\n'),
    );

    const result = injectToClaudeMd(handoffPath, projectRoot);

    assert.equal(result.success, true);
    assert.match(result.message, /Implement auth module/);

    const content = fs.readFileSync(claudeMdPath, 'utf8');
    assert.match(content, /<!-- HANDOFF:START -->/);
    assert.match(content, /<!-- HANDOFF:END -->/);
    assert.match(content, /\*\*Topic:\*\* Implement auth module/);
    assert.match(content, /2 completed, 1 pending/);
    assert.match(content, /Write integration tests/);
  });

  it('replaces existing markers instead of duplicating', () => {
    const claudeMdPath = path.join(projectRoot, 'CLAUDE.md');
    fs.writeFileSync(
      claudeMdPath,
      [
        '# My Project',
        '',
        '<!-- HANDOFF:START -->',
        '## Last Session Context',
        '**Topic:** Old topic',
        '<!-- HANDOFF:END -->',
        '',
        'Some other content',
      ].join('\n'),
    );

    const handoffPath = path.join(projectRoot, 'handoff.md');
    fs.writeFileSync(handoffPath, '**Topic:** New topic\n## Next Step\nDeploy');

    const result = injectToClaudeMd(handoffPath, projectRoot);

    assert.equal(result.success, true);

    const content = fs.readFileSync(claudeMdPath, 'utf8');
    // Old topic replaced
    assert.ok(!content.includes('Old topic'));
    assert.match(content, /New topic/);
    // Markers appear exactly once
    assert.equal(content.split('<!-- HANDOFF:START -->').length - 1, 1);
    assert.equal(content.split('<!-- HANDOFF:END -->').length - 1, 1);
    // Other content preserved
    assert.match(content, /Some other content/);
  });

  it('truncates long Next Step to 120 characters', () => {
    const claudeMdPath = path.join(projectRoot, 'CLAUDE.md');
    fs.writeFileSync(claudeMdPath, '# Project\n');

    const longStep = 'A'.repeat(200);
    const handoffPath = path.join(projectRoot, 'handoff.md');
    fs.writeFileSync(handoffPath, `**Topic:** My task\n## Next Step\n${longStep}`);

    const result = injectToClaudeMd(handoffPath, projectRoot);
    assert.equal(result.success, true);

    const content = fs.readFileSync(claudeMdPath, 'utf8');
    // Should contain truncated version ending with ...
    assert.match(content, /\.\.\.$/m);
    // The truncated next step should be at most 120 chars
    const nextMatch = content.match(/\*\*Next:\*\* (.+)/);
    assert.ok(nextMatch);
    assert.ok(nextMatch[1].length <= 120);
  });

  it('includes relative handoff path in the injected section', () => {
    const claudeMdPath = path.join(projectRoot, 'CLAUDE.md');
    fs.writeFileSync(claudeMdPath, '# Project\n');

    const handoffsDir = path.join(projectRoot, '.claude', 'handoffs');
    fs.mkdirSync(handoffsDir, { recursive: true });
    const handoffPath = path.join(handoffsDir, 'handoff-20250101-120000.md');
    fs.writeFileSync(handoffPath, '**Topic:** Test\n');

    injectToClaudeMd(handoffPath, projectRoot);

    const content = fs.readFileSync(claudeMdPath, 'utf8');
    assert.match(content, /\.claude\/handoffs\/handoff-20250101-120000\.md/);
  });
});

// ---------------------------------------------------------------------------
// formatStatsDisplay
// ---------------------------------------------------------------------------

describe('formatStatsDisplay', () => {
  it('returns unavailable message when stats is null', () => {
    const result = formatStatsDisplay(null);
    assert.match(result, /unavailable/);
  });

  it('returns unavailable message when stats is undefined', () => {
    const result = formatStatsDisplay(undefined);
    assert.match(result, /unavailable/);
  });

  it('formats valid stats into human-readable string', () => {
    const stats = {
      sessionTokens: 50000,
      handoffTokens: 500,
      compressionRatio: 100,
      savings: '99.0% saved',
    };

    const result = formatStatsDisplay(stats);

    assert.match(result, /50,000/);
    assert.match(result, /500/);
    assert.match(result, /100x/);
    assert.match(result, /99\.0% saved/);
  });

  it('formats small token counts correctly', () => {
    const stats = {
      sessionTokens: 100,
      handoffTokens: 25,
      compressionRatio: 4,
      savings: '75.0% saved',
    };

    const result = formatStatsDisplay(stats);
    assert.match(result, /Compression:/);
    assert.match(result, /4x/);
  });
});

// ---------------------------------------------------------------------------
// parseHandoffSections
// ---------------------------------------------------------------------------

describe('parseHandoffSections', () => {
  it('returns a Map with _preamble for content before first heading', () => {
    const content = 'Some preamble text\nLine 2\n## Section A\nBody A';
    const sections = parseHandoffSections(content);

    assert.ok(sections instanceof Map);
    assert.equal(sections.get('_preamble'), 'Some preamble text\nLine 2');
    assert.equal(sections.get('Section A'), 'Body A');
  });

  it('parses multiple sections correctly', () => {
    const content = [
      '**Topic:** My task',
      '## Completed',
      '- [x] Task 1',
      '- [x] Task 2',
      '## Pending',
      '- [ ] Task 3',
      '## Next Step',
      'Do the next thing',
    ].join('\n');

    const sections = parseHandoffSections(content);

    assert.equal(sections.size, 4); // _preamble + 3 sections
    assert.match(sections.get('Completed'), /Task 1/);
    assert.match(sections.get('Completed'), /Task 2/);
    assert.match(sections.get('Pending'), /Task 3/);
    assert.equal(sections.get('Next Step'), 'Do the next thing');
  });

  it('handles empty content', () => {
    const sections = parseHandoffSections('');
    assert.ok(sections instanceof Map);
    assert.equal(sections.get('_preamble'), '');
  });

  it('handles content with no sections (only preamble)', () => {
    const content = 'Just some text without headings';
    const sections = parseHandoffSections(content);

    assert.equal(sections.size, 1);
    assert.equal(sections.get('_preamble'), 'Just some text without headings');
  });

  it('trims section body content', () => {
    const content = '## Section\n\n  Body with leading space  \n\n';
    const sections = parseHandoffSections(content);
    assert.equal(sections.get('Section'), 'Body with leading space');
  });
});

// ---------------------------------------------------------------------------
// diffHandoffs
// ---------------------------------------------------------------------------

describe('diffHandoffs', () => {
  it('detects added list items in a list section', () => {
    const prev = new Map([
      ['_preamble', ''],
      ['Completed', '- [x] Task 1'],
    ]);
    const curr = new Map([
      ['_preamble', ''],
      ['Completed', '- [x] Task 1\n- [x] Task 2'],
    ]);

    const diff = diffHandoffs(prev, curr);

    assert.deepEqual(diff.added['Completed'], ['[x] Task 2']);
    assert.equal(diff.removed['Completed'], undefined);
  });

  it('detects removed list items in a list section', () => {
    const prev = new Map([
      ['_preamble', ''],
      ['Pending', '- [ ] Task A\n- [ ] Task B'],
    ]);
    const curr = new Map([
      ['_preamble', ''],
      ['Pending', '- [ ] Task B'],
    ]);

    const diff = diffHandoffs(prev, curr);

    assert.deepEqual(diff.removed['Pending'], ['[ ] Task A']);
  });

  it('detects changed prose sections', () => {
    const prev = new Map([
      ['_preamble', ''],
      ['Next Step', 'Do something old'],
    ]);
    const curr = new Map([
      ['_preamble', ''],
      ['Next Step', 'Do something new'],
    ]);

    const diff = diffHandoffs(prev, curr);

    assert.deepEqual(diff.changed['Next Step'], {
      from: 'Do something old',
      to: 'Do something new',
    });
  });

  it('marks identical sections as unchanged', () => {
    const prev = new Map([
      ['_preamble', ''],
      ['Constraints', '- No external deps'],
    ]);
    const curr = new Map([
      ['_preamble', ''],
      ['Constraints', '- No external deps'],
    ]);

    const diff = diffHandoffs(prev, curr);

    assert.ok(diff.unchanged.includes('Constraints'));
  });

  it('detects entirely new sections in current', () => {
    const prev = new Map([['_preamble', '']]);
    const curr = new Map([
      ['_preamble', ''],
      ['Key Decisions', '- Chose SQLite over Postgres'],
    ]);

    const diff = diffHandoffs(prev, curr);

    assert.deepEqual(diff.added['Key Decisions'], ['Chose SQLite over Postgres']);
  });

  it('detects sections removed in current', () => {
    const prev = new Map([
      ['_preamble', ''],
      ['Failed Approaches', '- Tried Redis caching'],
    ]);
    const curr = new Map([['_preamble', '']]);

    const diff = diffHandoffs(prev, curr);

    assert.deepEqual(diff.removed['Failed Approaches'], ['Tried Redis caching']);
  });

  it('skips _preamble from diff comparison', () => {
    const prev = new Map([['_preamble', 'old metadata']]);
    const curr = new Map([['_preamble', 'new metadata']]);

    const diff = diffHandoffs(prev, curr);

    assert.equal(Object.keys(diff.changed).length, 0);
    assert.equal(Object.keys(diff.added).length, 0);
    assert.equal(Object.keys(diff.removed).length, 0);
    assert.equal(diff.unchanged.length, 0);
  });

  it('handles new prose section (not a list section)', () => {
    const prev = new Map([['_preamble', '']]);
    const curr = new Map([
      ['_preamble', ''],
      ['Summary', 'A new summary was written'],
    ]);

    const diff = diffHandoffs(prev, curr);

    assert.deepEqual(diff.changed['Summary'], {
      from: '',
      to: 'A new summary was written',
    });
  });
});

// ---------------------------------------------------------------------------
// formatDiff
// ---------------------------------------------------------------------------

describe('formatDiff', () => {
  it('reports no changes when diff is empty', () => {
    const diff = { added: {}, removed: {}, changed: {}, unchanged: ['Completed'] };

    const result = formatDiff(diff);

    assert.match(result, /No changes detected/);
  });

  it('formats added items with + prefix', () => {
    const diff = {
      added: { 'Completed': ['Task A', 'Task B'] },
      removed: {},
      changed: {},
      unchanged: [],
    };

    const result = formatDiff(diff);

    assert.match(result, /\+ Task A/);
    assert.match(result, /\+ Task B/);
    assert.match(result, /## Completed/);
  });

  it('formats removed items with - prefix', () => {
    const diff = {
      added: {},
      removed: { 'Pending': ['Task X'] },
      changed: {},
      unchanged: [],
    };

    const result = formatDiff(diff);

    assert.match(result, /- Task X/);
  });

  it('formats changed prose sections with from/to', () => {
    const diff = {
      added: {},
      removed: {},
      changed: { 'Next Step': { from: 'Old step', to: 'New step' } },
      unchanged: [],
    };

    const result = formatDiff(diff);

    assert.match(result, /- Old step/);
    assert.match(result, /\+ New step/);
  });

  it('lists unchanged sections at the end', () => {
    const diff = {
      added: { 'Completed': ['New task'] },
      removed: {},
      changed: {},
      unchanged: ['Constraints', 'User Requests'],
    };

    const result = formatDiff(diff);

    assert.match(result, /Unchanged sections:.*Constraints.*User Requests/);
  });

  it('includes header in output', () => {
    const diff = {
      added: { 'Completed': ['Item'] },
      removed: {},
      changed: {},
      unchanged: [],
    };

    const result = formatDiff(diff);
    assert.match(result, /^# Handoff Diff/);
  });
});

// ---------------------------------------------------------------------------
// findRecentHandoffs
// ---------------------------------------------------------------------------

describe('findRecentHandoffs', () => {
  let handoffDir;

  beforeEach(() => {
    handoffDir = makeTempDir('handoffs-');
  });

  afterEach(() => {
    rmrf(handoffDir);
  });

  it('returns empty array for nonexistent directory', () => {
    const result = findRecentHandoffs('/tmp/nonexistent-dir-' + Date.now());
    assert.deepEqual(result, []);
  });

  it('returns empty array for directory with no handoff files', () => {
    fs.writeFileSync(path.join(handoffDir, 'random.txt'), 'data');
    const result = findRecentHandoffs(handoffDir);
    assert.deepEqual(result, []);
  });

  it('returns handoff files sorted newest-first by filename', () => {
    fs.writeFileSync(path.join(handoffDir, 'handoff-20250101-100000.md'), '');
    fs.writeFileSync(path.join(handoffDir, 'handoff-20250102-100000.md'), '');
    fs.writeFileSync(path.join(handoffDir, 'handoff-20250103-100000.md'), '');

    const result = findRecentHandoffs(handoffDir, 2);

    assert.equal(result.length, 2);
    assert.match(result[0], /20250103/);
    assert.match(result[1], /20250102/);
  });

  it('includes level-prefixed handoff files (l1, l2, l3)', () => {
    fs.writeFileSync(path.join(handoffDir, 'l1-20250101-100000.md'), '');
    fs.writeFileSync(path.join(handoffDir, 'l2-20250102-100000.md'), '');

    const result = findRecentHandoffs(handoffDir, 5);

    assert.equal(result.length, 2);
  });

  it('ignores non-handoff files', () => {
    fs.writeFileSync(path.join(handoffDir, 'handoff-20250101-100000.md'), '');
    fs.writeFileSync(path.join(handoffDir, 'stats.json'), '{}');
    fs.writeFileSync(path.join(handoffDir, 'notes.md'), '');

    const result = findRecentHandoffs(handoffDir, 10);

    assert.equal(result.length, 1);
  });
});

// ---------------------------------------------------------------------------
// loadIgnorePatterns
// ---------------------------------------------------------------------------

describe('loadIgnorePatterns', () => {
  let projectRoot;

  beforeEach(() => {
    projectRoot = makeTempDir('ignore-');
  });

  afterEach(() => {
    rmrf(projectRoot);
  });

  it('returns empty array when .handoffignore does not exist', () => {
    const result = loadIgnorePatterns(projectRoot);
    assert.deepEqual(result, []);
  });

  it('returns pattern lines from .handoffignore file', () => {
    fs.writeFileSync(
      path.join(projectRoot, '.handoffignore'),
      '*.log\nnode_modules/\n',
    );

    const result = loadIgnorePatterns(projectRoot);

    assert.deepEqual(result, ['*.log', 'node_modules/']);
  });

  it('skips comments and blank lines', () => {
    fs.writeFileSync(
      path.join(projectRoot, '.handoffignore'),
      '# This is a comment\n\n*.tmp\n   \n# Another comment\ndist/\n',
    );

    const result = loadIgnorePatterns(projectRoot);

    assert.deepEqual(result, ['*.tmp', 'dist/']);
  });

  it('returns empty array for an empty .handoffignore file', () => {
    fs.writeFileSync(path.join(projectRoot, '.handoffignore'), '');
    const result = loadIgnorePatterns(projectRoot);
    assert.deepEqual(result, []);
  });
});

// ---------------------------------------------------------------------------
// shouldIgnore
// ---------------------------------------------------------------------------

describe('shouldIgnore', () => {
  it('returns false when patterns list is empty', () => {
    assert.equal(shouldIgnore('src/index.js', []), false);
  });

  it('returns false when patterns is null', () => {
    assert.equal(shouldIgnore('src/index.js', null), false);
  });

  it('matches wildcard patterns', () => {
    assert.equal(shouldIgnore('debug.log', ['*.log']), true);
    assert.equal(shouldIgnore('src/app.js', ['*.log']), false);
  });

  it('matches directory patterns', () => {
    assert.equal(shouldIgnore('node_modules/express/index.js', ['node_modules/']), true);
  });

  it('matches double-star patterns for nested paths', () => {
    assert.equal(shouldIgnore('src/deep/nested/file.tmp', ['**/*.tmp']), true);
    assert.equal(shouldIgnore('file.tmp', ['**/*.tmp']), true);
  });

  it('supports negation patterns to re-include files', () => {
    const patterns = ['*.log', '!important.log'];
    assert.equal(shouldIgnore('debug.log', patterns), true);
    assert.equal(shouldIgnore('important.log', patterns), false);
  });

  it('normalises backslash paths to forward slashes', () => {
    assert.equal(shouldIgnore('src\\utils\\helper.log', ['*.log']), true);
  });

  it('returns false for files not matching any pattern', () => {
    assert.equal(shouldIgnore('src/main.ts', ['*.log', '*.tmp']), false);
  });
});

// ---------------------------------------------------------------------------
// filterFiles
// ---------------------------------------------------------------------------

describe('filterFiles', () => {
  let projectRoot;

  beforeEach(() => {
    projectRoot = makeTempDir('filter-');
  });

  afterEach(() => {
    rmrf(projectRoot);
  });

  it('returns all files when no .handoffignore exists', () => {
    const files = ['src/a.js', 'src/b.js'];
    const result = filterFiles(files, projectRoot);
    assert.deepEqual(result, files);
  });

  it('filters out files matching ignore patterns', () => {
    fs.writeFileSync(
      path.join(projectRoot, '.handoffignore'),
      '*.log\n*.tmp\n',
    );

    const files = ['src/app.js', 'debug.log', 'temp.tmp', 'README.md'];
    const result = filterFiles(files, projectRoot);

    assert.deepEqual(result, ['src/app.js', 'README.md']);
  });

  it('handles absolute paths by making them relative to projectRoot', () => {
    fs.writeFileSync(
      path.join(projectRoot, '.handoffignore'),
      '*.log\n',
    );

    const files = [
      path.join(projectRoot, 'src', 'app.js'),
      path.join(projectRoot, 'debug.log'),
    ];

    const result = filterFiles(files, projectRoot);

    assert.equal(result.length, 1);
    assert.match(result[0], /app\.js/);
  });

  it('returns empty array when all files are ignored', () => {
    fs.writeFileSync(
      path.join(projectRoot, '.handoffignore'),
      '*\n',
    );

    const files = ['a.js', 'b.ts'];
    const result = filterFiles(files, projectRoot);

    assert.deepEqual(result, []);
  });

  it('preserves files matching negation patterns', () => {
    fs.writeFileSync(
      path.join(projectRoot, '.handoffignore'),
      '*.log\n!important.log\n',
    );

    const files = ['debug.log', 'important.log', 'app.js'];
    const result = filterFiles(files, projectRoot);

    assert.deepEqual(result, ['important.log', 'app.js']);
  });
});
