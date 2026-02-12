import { describe, it, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, readFile, writeFile, mkdir, stat } from 'node:fs/promises';
import { existsSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import {
  generateId,
  ensureDir,
  loadState,
  saveState,
  acquireLock,
  releaseLock,
  isSessionMatch,
  checkStaleness,
  archiveState
} from '../../hooks/lib/state-manager.mjs';

describe('state-manager.mjs', () => {
  let tempDir;

  before(async () => {
    tempDir = await mkdtemp(join(tmpdir(), 'blueprint-test-'));
  });

  after(async () => {
    await rm(tempDir, { recursive: true, force: true });
  });

  describe('generateId()', () => {
    it('should return a string', () => {
      const id = generateId();
      assert.equal(typeof id, 'string');
    });

    it('should match format: YYYYMMDD-hexchars', () => {
      const id = generateId();
      // Format: 8-digit date + dash + 6-char hex
      assert.match(id, /^\d{8}-[0-9a-f]{6}$/);
    });

    it('should produce unique IDs on consecutive calls', () => {
      const ids = new Set();
      for (let i = 0; i < 100; i++) {
        ids.add(generateId());
      }
      // With 3 random bytes (16M possibilities), 100 should all be unique
      assert.equal(ids.size, 100);
    });

    it('should start with today date segment', () => {
      const id = generateId();
      const today = new Date().toISOString().slice(0, 10).replace(/-/g, '');
      assert.ok(id.startsWith(today), `ID "${id}" should start with "${today}"`);
    });
  });

  describe('ensureDir()', () => {
    it('should create a single directory', () => {
      const dir = join(tempDir, 'ensure-single');
      ensureDir(dir);
      assert.ok(existsSync(dir));
    });

    it('should create nested directories', () => {
      const dir = join(tempDir, 'ensure-nested', 'level1', 'level2');
      ensureDir(dir);
      assert.ok(existsSync(dir));
    });

    it('should not throw if directory already exists', () => {
      const dir = join(tempDir, 'ensure-existing');
      ensureDir(dir);
      assert.doesNotThrow(() => ensureDir(dir));
    });
  });

  describe('loadState()', () => {
    it('should return null for non-existent file', () => {
      const result = loadState(join(tempDir, 'nonexistent.json'));
      assert.equal(result, null);
    });

    it('should return parsed JSON for existing file', async () => {
      const filePath = join(tempDir, 'load-test.json');
      const data = { key: 'value', num: 42 };
      await writeFile(filePath, JSON.stringify(data));
      const result = loadState(filePath);
      assert.deepStrictEqual(result, data);
    });

    it('should return null for invalid JSON content', async () => {
      const filePath = join(tempDir, 'invalid.json');
      await writeFile(filePath, 'not-json{{{');
      const result = loadState(filePath);
      assert.equal(result, null);
    });
  });

  describe('saveState()', () => {
    it('should write a JSON file', () => {
      const filePath = join(tempDir, 'save-test.json');
      const data = { hello: 'world' };
      saveState(filePath, data);
      const content = loadState(filePath);
      assert.deepStrictEqual(content, data);
    });

    it('should write atomically via tmp file then rename', async () => {
      const filePath = join(tempDir, 'atomic-test.json');
      const data = { atomic: true };
      saveState(filePath, data);
      // The file should exist at the final path
      assert.ok(existsSync(filePath));
      // No .tmp file should remain
      const tmpPath = `${filePath}.tmp.${process.pid}`;
      assert.ok(!existsSync(tmpPath), 'temp file should not remain');
    });

    it('should create parent directories if they do not exist', () => {
      const filePath = join(tempDir, 'save-nested', 'deep', 'file.json');
      saveState(filePath, { nested: true });
      assert.ok(existsSync(filePath));
    });

    it('should write pretty-printed JSON with trailing newline', async () => {
      const filePath = join(tempDir, 'pretty-test.json');
      saveState(filePath, { a: 1 });
      const raw = await readFile(filePath, 'utf-8');
      assert.ok(raw.endsWith('\n'), 'should end with newline');
      assert.ok(raw.includes('\n'), 'should be multi-line (pretty printed)');
    });
  });

  describe('acquireLock() / releaseLock()', () => {
    it('should acquire and release a lock successfully', () => {
      const filePath = join(tempDir, 'lock-basic.json');
      const lock = acquireLock(filePath, { timeoutMs: 1000 });
      assert.ok(lock !== null, 'lock should be acquired');
      assert.equal(lock.pid, process.pid);
      assert.equal(typeof lock.timestamp, 'string');
      assert.equal(typeof lock.hostname, 'string');

      // Lock file should exist
      const lockPath = `${filePath}.lock`;
      assert.ok(existsSync(lockPath), 'lock file should exist');

      releaseLock(filePath);
      assert.ok(!existsSync(lockPath), 'lock file should be removed after release');
    });

    it('should detect and remove stale locks (older than staleMs)', () => {
      const filePath = join(tempDir, 'lock-stale.json');
      const lockPath = `${filePath}.lock`;

      // Create a stale lock manually (timestamp in the past)
      const staleLock = {
        pid: 99999999, // Non-existent PID
        timestamp: new Date(Date.now() - 60000).toISOString(), // 60s ago
        hostname: 'old-host'
      };
      ensureDir(tempDir);
      writeFileSync(lockPath, JSON.stringify(staleLock));

      // Should acquire by detecting stale lock
      const lock = acquireLock(filePath, { timeoutMs: 1000, staleMs: 30000 });
      assert.ok(lock !== null, 'should acquire lock after stale detection');
      assert.equal(lock.pid, process.pid);

      releaseLock(filePath);
    });

    it('releaseLock should not throw if lock does not exist', () => {
      const filePath = join(tempDir, 'lock-no-exist.json');
      assert.doesNotThrow(() => releaseLock(filePath));
    });
  });

  describe('isSessionMatch()', () => {
    it('should return true for matching session IDs', () => {
      const state = { sessionId: 'abc-123' };
      assert.equal(isSessionMatch(state, 'abc-123'), true);
    });

    it('should return false for non-matching session IDs', () => {
      const state = { sessionId: 'abc-123' };
      assert.equal(isSessionMatch(state, 'xyz-999'), false);
    });

    it('should return false for null state', () => {
      assert.equal(isSessionMatch(null, 'abc-123'), false);
    });

    it('should return false for null sessionId', () => {
      assert.equal(isSessionMatch({ sessionId: 'abc' }, null), false);
    });

    it('should return false for undefined sessionId', () => {
      assert.equal(isSessionMatch({ sessionId: 'abc' }, undefined), false);
    });

    it('should return false for state without sessionId field', () => {
      assert.equal(isSessionMatch({ other: 'data' }, 'abc'), false);
    });
  });

  describe('checkStaleness()', () => {
    it('should return true for null state', () => {
      assert.equal(checkStaleness(null, 1000), true);
    });

    it('should return true for state without timestamp fields', () => {
      assert.equal(checkStaleness({ data: 'value' }, 1000), true);
    });

    it('should return false for fresh state (updatedAt)', () => {
      const state = { updatedAt: new Date().toISOString() };
      assert.equal(checkStaleness(state, 60000), false);
    });

    it('should return true for stale state (updatedAt)', () => {
      const state = { updatedAt: new Date(Date.now() - 120000).toISOString() };
      assert.equal(checkStaleness(state, 60000), true);
    });

    it('should use createdAt as fallback when updatedAt is absent', () => {
      const state = { createdAt: new Date().toISOString() };
      assert.equal(checkStaleness(state, 60000), false);
    });

    it('should prefer updatedAt over createdAt', () => {
      const state = {
        createdAt: new Date(Date.now() - 120000).toISOString(), // stale
        updatedAt: new Date().toISOString() // fresh
      };
      assert.equal(checkStaleness(state, 60000), false);
    });
  });

  describe('archiveState()', () => {
    it('should move file to history directory with timestamp', async () => {
      const sourceDir = join(tempDir, 'archive-src');
      const historyDir = join(tempDir, 'archive-history');
      ensureDir(sourceDir);

      const sourcePath = join(sourceDir, 'cycle-1.json');
      saveState(sourcePath, { id: 'cycle-1', status: 'completed' });

      const archivePath = archiveState(sourcePath, historyDir);

      // Source should be removed
      assert.ok(!existsSync(sourcePath), 'source file should be removed');
      // Archive should exist
      assert.ok(existsSync(archivePath), 'archive file should exist');
      // Archive should contain the data
      const archived = loadState(archivePath);
      assert.equal(archived.id, 'cycle-1');
    });

    it('should create history directory if it does not exist', () => {
      const sourceDir = join(tempDir, 'archive-src2');
      const historyDir = join(tempDir, 'archive-new-history');
      ensureDir(sourceDir);

      const sourcePath = join(sourceDir, 'cycle-2.json');
      saveState(sourcePath, { id: 'cycle-2' });

      archiveState(sourcePath, historyDir);
      assert.ok(existsSync(historyDir), 'history directory should be created');
    });

    it('should return archive path even if source does not exist', () => {
      const historyDir = join(tempDir, 'archive-empty-history');
      const sourcePath = join(tempDir, 'nonexistent-archive.json');
      const result = archiveState(sourcePath, historyDir);
      assert.equal(typeof result, 'string');
    });
  });
});
