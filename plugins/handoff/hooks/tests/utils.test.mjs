/**
 * Utils Module Tests
 *
 * Covers: estimateTokens, trackTokenUsage (callId uniqueness + dedup),
 *         acquireLock/releaseLock, loadJsonState/saveJsonState/saveJsonStateAtomic
 */

import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'fs';
import * as path from 'path';
import { tmpdir } from 'os';
import * as crypto from 'crypto';

import {
  estimateTokens,
  acquireLock,
  releaseLock,
  loadJsonState,
  saveJsonState,
  saveJsonStateAtomic,
  trackTokenUsage,
  getSharedTokenCount,
  DEFAULT_LOCK_TIMEOUT_MS,
} from '../utils.mjs';

import { CHARS_PER_TOKEN } from '../constants.mjs';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Generate a unique temp path to avoid collisions between tests */
function tempPath(suffix = '') {
  return path.join(
    tmpdir(),
    `handoff-test-${crypto.randomBytes(6).toString('hex')}${suffix}`,
  );
}

// ---------------------------------------------------------------------------
// estimateTokens
// ---------------------------------------------------------------------------

describe('estimateTokens', () => {
  it('returns 0 for an empty string', () => {
    assert.equal(estimateTokens(''), 0);
  });

  it('returns 1 for a string shorter than CHARS_PER_TOKEN', () => {
    // 1-3 chars should still ceil to 1 token
    assert.equal(estimateTokens('abc'), 1);
  });

  it('returns correct count for exact multiple of CHARS_PER_TOKEN', () => {
    const text = 'a'.repeat(CHARS_PER_TOKEN * 10); // 40 chars
    assert.equal(estimateTokens(text), 10);
  });

  it('rounds up for non-exact multiples', () => {
    const text = 'a'.repeat(CHARS_PER_TOKEN * 10 + 1); // 41 chars
    assert.equal(estimateTokens(text), 11);
  });

  it('handles large inputs consistently', () => {
    const text = 'x'.repeat(100_000);
    assert.equal(estimateTokens(text), Math.ceil(100_000 / CHARS_PER_TOKEN));
  });
});

// ---------------------------------------------------------------------------
// acquireLock / releaseLock
// ---------------------------------------------------------------------------

describe('acquireLock / releaseLock', () => {
  let lockFile;

  beforeEach(() => {
    lockFile = tempPath('.lock');
  });

  afterEach(() => {
    try { fs.unlinkSync(lockFile); } catch { /* noop */ }
  });

  it('acquires a fresh lock successfully', () => {
    assert.equal(acquireLock(lockFile), true);
    assert.equal(fs.existsSync(lockFile), true);
    releaseLock(lockFile);
  });

  it('releases the lock file from disk', () => {
    acquireLock(lockFile);
    releaseLock(lockFile);
    assert.equal(fs.existsSync(lockFile), false);
  });

  it('fails to acquire when lock is already held', () => {
    acquireLock(lockFile);
    // Second acquire with a very short timeout should fail
    assert.equal(acquireLock(lockFile, 100), false);
    releaseLock(lockFile);
  });

  it('releaseLock is safe to call when no lock exists', () => {
    // Should not throw
    releaseLock(lockFile);
  });

  it('reclaims a stale lock older than timeout', () => {
    // Create a lock file with an old mtime
    fs.writeFileSync(lockFile, '99999', { flag: 'wx', mode: 0o600 });
    const past = new Date(Date.now() - 10_000); // 10 seconds ago
    fs.utimesSync(lockFile, past, past);

    // Acquire with a 5-second timeout should reclaim the stale lock
    assert.equal(acquireLock(lockFile, 5000), true);
    releaseLock(lockFile);
  });
});

// ---------------------------------------------------------------------------
// loadJsonState / saveJsonState / saveJsonStateAtomic
// ---------------------------------------------------------------------------

describe('loadJsonState / saveJsonState', () => {
  let stateFile;

  beforeEach(() => {
    stateFile = tempPath('.json');
  });

  afterEach(() => {
    try { fs.unlinkSync(stateFile); } catch { /* noop */ }
    try { fs.unlinkSync(stateFile + '.tmp'); } catch { /* noop */ }
  });

  it('returns default value when file does not exist', () => {
    const result = loadJsonState(stateFile, { count: 0 });
    assert.deepEqual(result, { count: 0 });
  });

  it('returns default value when file contains invalid JSON', () => {
    fs.writeFileSync(stateFile, 'NOT_JSON!!!');
    const result = loadJsonState(stateFile, []);
    assert.deepEqual(result, []);
  });

  it('round-trips data through saveJsonState and loadJsonState', () => {
    const data = { sessions: { abc: { tokens: 42 } } };
    saveJsonState(stateFile, data);
    const loaded = loadJsonState(stateFile);
    assert.deepEqual(loaded, data);
  });

  it('saveJsonStateAtomic writes data that loadJsonState can read', () => {
    const data = { key: 'value', nested: { a: 1 } };
    saveJsonStateAtomic(stateFile, data);
    const loaded = loadJsonState(stateFile);
    assert.deepEqual(loaded, data);
  });

  it('saveJsonStateAtomic does not leave .tmp file behind', () => {
    saveJsonStateAtomic(stateFile, { ok: true });
    assert.equal(fs.existsSync(stateFile + '.tmp'), false);
  });
});

// ---------------------------------------------------------------------------
// trackTokenUsage — callId uniqueness & deduplication
// ---------------------------------------------------------------------------

describe('trackTokenUsage', () => {
  let stateFile;
  const SESSION = 'test-session-' + Date.now();

  beforeEach(() => {
    // trackTokenUsage uses SHARED_TOKEN_STATE_PATH which is derived from
    // constants.SHARED_TOKEN_STATE_FILE in tmpdir. We need to clean it up.
    stateFile = path.join(tmpdir(), 'shared-token-state.json');
    // Remove any prior state for our test session
    try {
      const state = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
      delete state[SESSION];
      fs.writeFileSync(stateFile, JSON.stringify(state, null, 2));
    } catch { /* file may not exist */ }
    // Also clean lock file
    try { fs.unlinkSync(stateFile + '.lock'); } catch { /* noop */ }
  });

  afterEach(() => {
    try {
      const state = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
      delete state[SESSION];
      fs.writeFileSync(stateFile, JSON.stringify(state, null, 2));
    } catch { /* noop */ }
    try { fs.unlinkSync(stateFile + '.lock'); } catch { /* noop */ }
  });

  it('returns estimated tokens after first call', () => {
    const response = 'hello world'; // 11 chars => ceil(11/4) = 3 tokens
    const result = trackTokenUsage(SESSION, 'Read', response);
    assert.equal(result, Math.ceil(response.length / CHARS_PER_TOKEN));
  });

  it('accumulates tokens across different tool calls', () => {
    const r1 = 'a'.repeat(100); // 25 tokens
    const r2 = 'b'.repeat(200); // 50 tokens

    trackTokenUsage(SESSION, 'Read', r1);
    const total = trackTokenUsage(SESSION, 'Write', r2);

    assert.equal(total, 25 + 50);
  });

  it('deduplicates the same callId (same tool + same response length)', () => {
    const response = 'x'.repeat(80); // 20 tokens

    const first = trackTokenUsage(SESSION, 'Read', response);
    const second = trackTokenUsage(SESSION, 'Read', response);

    // Second call with identical callId should NOT add tokens again
    assert.equal(first, second);
  });

  it('generates distinct callIds for different response lengths even with same tool', () => {
    const r1 = 'a'.repeat(40);  // callId = "Read:40"
    const r2 = 'a'.repeat(80);  // callId = "Read:80"

    const after1 = trackTokenUsage(SESSION, 'Read', r1);
    const after2 = trackTokenUsage(SESSION, 'Read', r2);

    assert.ok(after2 > after1, 'Different response lengths should produce different callIds and accumulate');
  });

  it('generates distinct callIds for different tools with same response length', () => {
    const response = 'same content here'; // length 17 for both

    const after1 = trackTokenUsage(SESSION, 'Read', response);
    // Reset lastCallId by using a different tool name
    const after2 = trackTokenUsage(SESSION, 'Write', response);

    assert.ok(after2 > after1, 'Different tool names should produce different callIds and accumulate');
  });
});

// ---------------------------------------------------------------------------
// getSharedTokenCount
// ---------------------------------------------------------------------------

describe('getSharedTokenCount', () => {
  it('returns 0 for an unknown session', () => {
    assert.equal(getSharedTokenCount('nonexistent-session-xyz'), 0);
  });
});
