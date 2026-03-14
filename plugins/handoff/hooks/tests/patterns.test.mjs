/**
 * Filename Pattern Matching Tests
 *
 * Regression tests for Bug 1-1 (handoff-*.md patterns) and Bug 1-2 (cooldown check).
 *
 * Covers:
 *   - handoff-*.md, l1-*.md, l2-*.md, l3-*.md pattern matching (session-restore)
 *   - checkpoint-*.md additional pattern (auto-checkpoint cooldown)
 *   - Cooldown check logic with recent vs old files
 */

import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'fs';
import * as path from 'path';
import { tmpdir } from 'os';
import * as crypto from 'crypto';

// ---------------------------------------------------------------------------
// Helpers — extract regex patterns used by the production code
// ---------------------------------------------------------------------------

/**
 * Regex used by session-restore.mjs findHandoffFiles() to match handoff filenames.
 * Extracted so we test the exact same pattern.
 */
const HANDOFF_FILE_PATTERN = /^(handoff|l[123])-.*\.md$/;

/**
 * Regex used by auto-checkpoint.mjs checkRecentCheckpoint() for cooldown.
 * Includes 'checkpoint-' prefix in addition to handoff patterns.
 */
const CHECKPOINT_FILE_PATTERN = /^(handoff|l[123]|checkpoint)-.*\.md$/;

/** Create a unique temp directory for each test run */
function makeTempDir() {
  const dir = path.join(tmpdir(), `pattern-test-${crypto.randomBytes(6).toString('hex')}`);
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

/** Remove a temp directory and all its contents */
function removeTempDir(dir) {
  try {
    fs.rmSync(dir, { recursive: true, force: true });
  } catch { /* noop */ }
}

// ---------------------------------------------------------------------------
// Handoff file pattern matching (session-restore)
// ---------------------------------------------------------------------------

describe('Handoff filename pattern matching', () => {

  // -- Should match --

  it('matches handoff-*.md files', () => {
    assert.ok(HANDOFF_FILE_PATTERN.test('handoff-20260214-163040-2612.md'));
  });

  it('matches handoff with descriptive slug', () => {
    assert.ok(HANDOFF_FILE_PATTERN.test('handoff-my-task-summary.md'));
  });

  it('matches l1-*.md files', () => {
    assert.ok(HANDOFF_FILE_PATTERN.test('l1-some-topic.md'));
  });

  it('matches l2-*.md files', () => {
    assert.ok(HANDOFF_FILE_PATTERN.test('l2-another-topic.md'));
  });

  it('matches l3-*.md files', () => {
    assert.ok(HANDOFF_FILE_PATTERN.test('l3-deep-context.md'));
  });

  it('matches l1 with timestamp-style naming', () => {
    assert.ok(HANDOFF_FILE_PATTERN.test('l1-20260314-120000-abcd.md'));
  });

  // -- Should NOT match --

  it('does not match .json files', () => {
    assert.ok(!HANDOFF_FILE_PATTERN.test('handoff-data.json'));
  });

  it('does not match files without hyphen after prefix', () => {
    assert.ok(!HANDOFF_FILE_PATTERN.test('handoff.md'));
  });

  it('does not match l4 prefix (only l1-l3 supported)', () => {
    assert.ok(!HANDOFF_FILE_PATTERN.test('l4-extra.md'));
  });

  it('does not match l0 prefix', () => {
    assert.ok(!HANDOFF_FILE_PATTERN.test('l0-base.md'));
  });

  it('does not match random markdown files', () => {
    assert.ok(!HANDOFF_FILE_PATTERN.test('README.md'));
  });

  it('does not match checkpoint prefix (not part of handoff restore)', () => {
    assert.ok(!HANDOFF_FILE_PATTERN.test('checkpoint-123.md'));
  });

  it('does not match draft files', () => {
    assert.ok(!HANDOFF_FILE_PATTERN.test('.draft-handoff.md'));
  });

  it('does not match pre-compact snapshots', () => {
    assert.ok(!HANDOFF_FILE_PATTERN.test('.pre-compact-session.json'));
  });
});

// ---------------------------------------------------------------------------
// Checkpoint file pattern matching (auto-checkpoint cooldown)
// ---------------------------------------------------------------------------

describe('Checkpoint filename pattern matching', () => {

  it('matches handoff-*.md files', () => {
    assert.ok(CHECKPOINT_FILE_PATTERN.test('handoff-session-001.md'));
  });

  it('matches l1-*.md files', () => {
    assert.ok(CHECKPOINT_FILE_PATTERN.test('l1-work.md'));
  });

  it('matches l2-*.md files', () => {
    assert.ok(CHECKPOINT_FILE_PATTERN.test('l2-work.md'));
  });

  it('matches l3-*.md files', () => {
    assert.ok(CHECKPOINT_FILE_PATTERN.test('l3-work.md'));
  });

  it('matches checkpoint-*.md files', () => {
    assert.ok(CHECKPOINT_FILE_PATTERN.test('checkpoint-auto-20260314.md'));
  });

  it('does not match arbitrary markdown files', () => {
    assert.ok(!CHECKPOINT_FILE_PATTERN.test('notes.md'));
  });
});

// ---------------------------------------------------------------------------
// Cooldown check — filesystem integration
// ---------------------------------------------------------------------------

describe('Cooldown check with recent files', () => {
  let tempDir;
  const COOLDOWN_MINUTES = 25;
  const COOLDOWN_MS = COOLDOWN_MINUTES * 60 * 1000;

  beforeEach(() => {
    tempDir = makeTempDir();
  });

  afterEach(() => {
    removeTempDir(tempDir);
  });

  /**
   * Simulate checkRecentCheckpoint logic from auto-checkpoint.mjs
   * Extracted here so we can test it without needing stdin/process setup.
   */
  function hasRecentCheckpoint(dir, cooldownMs) {
    try {
      if (!fs.existsSync(dir)) return false;
      const files = fs.readdirSync(dir);
      const now = Date.now();

      for (const file of files) {
        if (CHECKPOINT_FILE_PATTERN.test(file)) {
          const stat = fs.statSync(path.join(dir, file));
          if (now - stat.mtimeMs < cooldownMs) {
            return true;
          }
        }
      }
    } catch {
      // noop
    }
    return false;
  }

  it('returns false when directory is empty', () => {
    assert.equal(hasRecentCheckpoint(tempDir, COOLDOWN_MS), false);
  });

  it('returns false when directory does not exist', () => {
    assert.equal(hasRecentCheckpoint('/nonexistent/path', COOLDOWN_MS), false);
  });

  it('returns true when a recent handoff file exists within cooldown', () => {
    const filePath = path.join(tempDir, 'handoff-test-recent.md');
    fs.writeFileSync(filePath, '# Recent handoff');
    // File just created => mtime is now => within cooldown
    assert.equal(hasRecentCheckpoint(tempDir, COOLDOWN_MS), true);
  });

  it('returns true when a recent checkpoint file exists within cooldown', () => {
    const filePath = path.join(tempDir, 'checkpoint-auto-20260314.md');
    fs.writeFileSync(filePath, '# Checkpoint');
    assert.equal(hasRecentCheckpoint(tempDir, COOLDOWN_MS), true);
  });

  it('returns true when a recent l1 file exists within cooldown', () => {
    const filePath = path.join(tempDir, 'l1-topic.md');
    fs.writeFileSync(filePath, '# L1 handoff');
    assert.equal(hasRecentCheckpoint(tempDir, COOLDOWN_MS), true);
  });

  it('returns false when only old files exist (beyond cooldown)', () => {
    const filePath = path.join(tempDir, 'handoff-old-session.md');
    fs.writeFileSync(filePath, '# Old handoff');
    // Set mtime to 2 hours ago (well beyond 25-min cooldown)
    const past = new Date(Date.now() - 2 * 60 * 60 * 1000);
    fs.utimesSync(filePath, past, past);
    assert.equal(hasRecentCheckpoint(tempDir, COOLDOWN_MS), false);
  });

  it('returns false when only non-matching files exist', () => {
    fs.writeFileSync(path.join(tempDir, 'README.md'), '# readme');
    fs.writeFileSync(path.join(tempDir, 'notes.txt'), 'notes');
    assert.equal(hasRecentCheckpoint(tempDir, COOLDOWN_MS), false);
  });

  it('ignores .json files even with matching prefix', () => {
    fs.writeFileSync(path.join(tempDir, 'handoff-data.json'), '{}');
    assert.equal(hasRecentCheckpoint(tempDir, COOLDOWN_MS), false);
  });
});
