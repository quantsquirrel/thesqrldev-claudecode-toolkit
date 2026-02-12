import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const serverPath = join(__dirname, '..', '..', 'mcp', 'blueprint-server.cjs');

/**
 * Helper: send a JSON-RPC request to the MCP server and get the response.
 * Spawns the server, writes a newline-delimited JSON-RPC message, reads response.
 */
function sendJsonRpc(request, timeoutMs = 5000) {
  return new Promise((resolve, reject) => {
    const child = spawn('node', [serverPath], {
      stdio: ['pipe', 'pipe', 'pipe'],
      cwd: '/tmp'
    });

    let stdout = '';
    let stderr = '';
    let settled = false;

    const timer = setTimeout(() => {
      if (!settled) {
        settled = true;
        child.kill('SIGKILL');
        reject(new Error(`MCP server timed out after ${timeoutMs}ms`));
      }
    }, timeoutMs);

    child.stdout.on('data', (data) => {
      stdout += data.toString();
      // Check if we have a complete JSON line
      const lines = stdout.split('\n').filter(l => l.trim());
      if (lines.length > 0) {
        try {
          const parsed = JSON.parse(lines[lines.length - 1]);
          if (!settled) {
            settled = true;
            clearTimeout(timer);
            child.stdin.end();
            child.kill('SIGTERM');
            resolve(parsed);
          }
        } catch {
          // Not yet complete JSON, wait for more data
        }
      }
    });

    child.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    child.on('error', (err) => {
      if (!settled) {
        settled = true;
        clearTimeout(timer);
        reject(err);
      }
    });

    child.on('close', (code) => {
      if (!settled) {
        settled = true;
        clearTimeout(timer);
        if (stdout.trim()) {
          try {
            const lines = stdout.split('\n').filter(l => l.trim());
            resolve(JSON.parse(lines[lines.length - 1]));
          } catch {
            reject(new Error(`Server closed with unparseable output: ${stdout}`));
          }
        } else {
          reject(new Error(`Server closed with code ${code}, stderr: ${stderr}`));
        }
      }
    });

    // Send JSON-RPC message as newline-delimited JSON
    child.stdin.write(JSON.stringify(request) + '\n');
  });
}

/**
 * Helper: send multiple JSON-RPC requests sequentially and get all responses.
 */
function sendMultipleJsonRpc(requests, timeoutMs = 5000) {
  return new Promise((resolve, reject) => {
    const child = spawn('node', [serverPath], {
      stdio: ['pipe', 'pipe', 'pipe'],
      cwd: '/tmp'
    });

    let stdout = '';
    let settled = false;
    const responses = [];

    const timer = setTimeout(() => {
      if (!settled) {
        settled = true;
        child.kill('SIGKILL');
        // Return whatever we have
        resolve(responses);
      }
    }, timeoutMs);

    child.stdout.on('data', (data) => {
      stdout += data.toString();
      const lines = stdout.split('\n');
      // Process complete lines
      while (lines.length > 1) {
        const line = lines.shift().trim();
        if (line) {
          try {
            responses.push(JSON.parse(line));
          } catch {
            // skip invalid lines
          }
        }
      }
      stdout = lines[0] || '';

      if (responses.length >= requests.length && !settled) {
        settled = true;
        clearTimeout(timer);
        child.stdin.end();
        child.kill('SIGTERM');
        resolve(responses);
      }
    });

    child.on('error', (err) => {
      if (!settled) {
        settled = true;
        clearTimeout(timer);
        reject(err);
      }
    });

    child.on('close', () => {
      if (!settled) {
        settled = true;
        clearTimeout(timer);
        // Parse any remaining
        if (stdout.trim()) {
          try { responses.push(JSON.parse(stdout.trim())); } catch { /* skip */ }
        }
        resolve(responses);
      }
    });

    // Send all requests
    for (const req of requests) {
      child.stdin.write(JSON.stringify(req) + '\n');
    }
  });
}

describe('blueprint-server.cjs JSON-RPC protocol', () => {

  describe('initialize', () => {
    it('should return capabilities and serverInfo', async () => {
      const response = await sendJsonRpc({
        jsonrpc: '2.0',
        id: 1,
        method: 'initialize',
        params: {}
      });

      assert.equal(response.jsonrpc, '2.0');
      assert.equal(response.id, 1);
      assert.ok(response.result, 'should have result');
      assert.ok(response.result.capabilities, 'should have capabilities');
      assert.ok(response.result.serverInfo, 'should have serverInfo');
      assert.equal(response.result.serverInfo.name, 'blueprint');
      assert.equal(typeof response.result.serverInfo.version, 'string');
    });
  });

  describe('tools/list', () => {
    it('should list 5 tools: pdca_status, gap_measure, pipeline_progress, pdca_update, pipeline_advance', async () => {
      const response = await sendJsonRpc({
        jsonrpc: '2.0',
        id: 2,
        method: 'tools/list',
        params: {}
      });

      assert.equal(response.jsonrpc, '2.0');
      assert.equal(response.id, 2);
      assert.ok(response.result, 'should have result');
      assert.ok(Array.isArray(response.result.tools), 'tools should be an array');
      assert.equal(response.result.tools.length, 5);

      const toolNames = response.result.tools.map(t => t.name);
      assert.ok(toolNames.includes('pdca_status'));
      assert.ok(toolNames.includes('gap_measure'));
      assert.ok(toolNames.includes('pipeline_progress'));
      assert.ok(toolNames.includes('pdca_update'));
      assert.ok(toolNames.includes('pipeline_advance'));
    });

    it('each tool should have name, description, and inputSchema', async () => {
      const response = await sendJsonRpc({
        jsonrpc: '2.0',
        id: 3,
        method: 'tools/list',
        params: {}
      });

      for (const tool of response.result.tools) {
        assert.equal(typeof tool.name, 'string');
        assert.equal(typeof tool.description, 'string');
        assert.ok(tool.inputSchema, `tool ${tool.name} should have inputSchema`);
        assert.equal(tool.inputSchema.type, 'object');
      }
    });
  });

  describe('tools/call', () => {
    it('pdca_status should return valid result with content array', async () => {
      const response = await sendJsonRpc({
        jsonrpc: '2.0',
        id: 10,
        method: 'tools/call',
        params: { name: 'pdca_status', arguments: {} }
      });

      assert.equal(response.jsonrpc, '2.0');
      assert.equal(response.id, 10);
      assert.ok(response.result, 'should have result');
      assert.ok(Array.isArray(response.result.content), 'result should have content array');
      assert.ok(response.result.content.length > 0, 'content array should not be empty');
      assert.equal(response.result.content[0].type, 'text');
      assert.equal(typeof response.result.content[0].text, 'string');

      // Parse the text to verify it's valid JSON
      const parsed = JSON.parse(response.result.content[0].text);
      assert.ok('cycles' in parsed, 'pdca_status output should have cycles key');
    });

    it('gap_measure should return valid result with content array', async () => {
      const response = await sendJsonRpc({
        jsonrpc: '2.0',
        id: 11,
        method: 'tools/call',
        params: { name: 'gap_measure', arguments: {} }
      });

      assert.equal(response.jsonrpc, '2.0');
      assert.equal(response.id, 11);
      assert.ok(response.result);
      assert.ok(Array.isArray(response.result.content));
      assert.equal(response.result.content[0].type, 'text');

      const parsed = JSON.parse(response.result.content[0].text);
      assert.ok('analyses' in parsed, 'gap_measure output should have analyses key');
    });

    it('pipeline_progress should return valid result with content array', async () => {
      const response = await sendJsonRpc({
        jsonrpc: '2.0',
        id: 12,
        method: 'tools/call',
        params: { name: 'pipeline_progress', arguments: {} }
      });

      assert.equal(response.jsonrpc, '2.0');
      assert.equal(response.id, 12);
      assert.ok(response.result);
      assert.ok(Array.isArray(response.result.content));
      assert.equal(response.result.content[0].type, 'text');

      const parsed = JSON.parse(response.result.content[0].text);
      assert.ok('pipelines' in parsed, 'pipeline_progress output should have pipelines key');
    });

    it('unknown tool should return error', async () => {
      const response = await sendJsonRpc({
        jsonrpc: '2.0',
        id: 20,
        method: 'tools/call',
        params: { name: 'nonexistent_tool', arguments: {} }
      });

      assert.equal(response.jsonrpc, '2.0');
      assert.equal(response.id, 20);
      assert.ok(response.error, 'should have error');
      assert.equal(typeof response.error.message, 'string');
    });
  });

  describe('unknown method', () => {
    it('should return error for unknown method', async () => {
      const response = await sendJsonRpc({
        jsonrpc: '2.0',
        id: 30,
        method: 'nonexistent/method',
        params: {}
      });

      assert.equal(response.jsonrpc, '2.0');
      assert.equal(response.id, 30);
      assert.ok(response.error, 'should have error for unknown method');
    });
  });
});
