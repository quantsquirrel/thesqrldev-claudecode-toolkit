import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const hooksDir = join(__dirname, '..', '..', 'hooks');

/**
 * Helper: spawn a hook script, pipe JSON to its stdin, capture stdout.
 * Uses spawn with explicit stdin.write/stdin.end for reliable input delivery.
 * Uses a temp directory as cwd to avoid polluting project directory.
 */
async function runHook(scriptPath, inputObj, timeoutMs = 10000) {
  const tmpDir = await mkdtemp(join(tmpdir(), 'hook-test-'));
  try {
    const input = JSON.stringify(inputObj);
    return await new Promise((resolve, reject) => {
      const child = spawn('node', [scriptPath], {
        stdio: ['pipe', 'pipe', 'pipe'],
        cwd: tmpDir,
        env: { ...process.env, HOME: tmpDir }
      });

      let stdout = '';
      let settled = false;

      const timer = setTimeout(() => {
        if (!settled) {
          settled = true;
          child.kill('SIGKILL');
          reject(new Error(`Hook timed out after ${timeoutMs}ms`));
        }
      }, timeoutMs);

      child.stdout.on('data', (data) => { stdout += data.toString(); });

      child.on('close', () => {
        if (!settled) {
          settled = true;
          clearTimeout(timer);
          try {
            resolve(JSON.parse(stdout.trim()));
          } catch (e) {
            reject(new Error(`Failed to parse hook output: "${stdout}"`));
          }
        }
      });

      child.on('error', (err) => {
        if (!settled) {
          settled = true;
          clearTimeout(timer);
          reject(err);
        }
      });

      // Write input and close stdin to signal EOF
      child.stdin.write(input);
      child.stdin.end();
    });
  } finally {
    await rm(tmpDir, { recursive: true, force: true });
  }
}

describe('hooks I/O contracts', () => {

  describe('blueprint-detect.mjs', () => {
    const scriptPath = join(hooksDir, 'blueprint-detect.mjs');

    it('should return valid JSON with continue field for plain input', async () => {
      const result = await runHook(scriptPath, { cwd: '/tmp', input: 'test' });
      assert.equal(typeof result, 'object');
      assert.equal(result.continue, true);
    });

    it('should return continue:true when no blueprint keyword matched', async () => {
      const result = await runHook(scriptPath, { prompt: 'hello world' });
      assert.equal(result.continue, true);
    });

    it('should detect /blueprint:pdca keyword and return additionalContext', async () => {
      const result = await runHook(scriptPath, { prompt: '/blueprint:pdca improve auth' });
      assert.equal(result.continue, true);
      assert.ok(result.hookSpecificOutput, 'should have hookSpecificOutput');
      assert.ok(
        result.hookSpecificOutput.additionalContext.includes('PDCA'),
        'additionalContext should mention PDCA'
      );
    });
  });

  describe('phase-tracker.mjs', () => {
    const scriptPath = join(hooksDir, 'phase-tracker.mjs');

    it('should return valid JSON with continue:true for Write tool', async () => {
      const result = await runHook(scriptPath, {
        cwd: '/tmp',
        tool_name: 'Write',
        tool_input: {}
      });
      assert.equal(typeof result, 'object');
      assert.equal(result.continue, true);
    });

    it('should return continue:true for untracked tool', async () => {
      const result = await runHook(scriptPath, {
        cwd: '/tmp',
        tool_name: 'Read',
        tool_input: {}
      });
      assert.equal(result.continue, true);
    });
  });

  describe('session-loader.mjs', () => {
    const scriptPath = join(hooksDir, 'session-loader.mjs');

    it('should return valid JSON with continue field', async () => {
      const result = await runHook(scriptPath, { cwd: '/tmp' });
      assert.equal(typeof result, 'object');
      assert.equal(result.continue, true);
    });
  });

  describe('compact-preserver.mjs', () => {
    const scriptPath = join(hooksDir, 'compact-preserver.mjs');

    it('should return valid JSON with continue:true', async () => {
      const result = await runHook(scriptPath, { cwd: '/tmp' });
      assert.equal(typeof result, 'object');
      assert.equal(result.continue, true);
    });
  });

  describe('cycle-finalize.cjs', () => {
    const scriptPath = join(hooksDir, 'cycle-finalize.cjs');

    it('should return valid JSON with continue:true', async () => {
      const result = await runHook(scriptPath, { cwd: '/tmp' });
      assert.equal(typeof result, 'object');
      assert.equal(result.continue, true);
    });
  });

  describe('session-cleanup.mjs', () => {
    const scriptPath = join(hooksDir, 'session-cleanup.mjs');

    it('should return valid JSON with continue:true', async () => {
      const result = await runHook(scriptPath, { cwd: '/tmp' });
      assert.equal(typeof result, 'object');
      assert.equal(result.continue, true);
    });
  });
});
