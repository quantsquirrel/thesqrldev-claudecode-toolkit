import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..', '..');

/**
 * Helper: read and parse a JSON config file.
 */
function readJsonConfig(relativePath) {
  const filePath = join(projectRoot, relativePath);
  const raw = readFileSync(filePath, 'utf-8');
  return JSON.parse(raw);
}

describe('config file validation', () => {

  describe('config/pdca-defaults.json', () => {
    let config;

    it('should be valid JSON', () => {
      config = readJsonConfig('config/pdca-defaults.json');
      assert.ok(config, 'should parse without error');
    });

    it('should have max_iterations field as a number', () => {
      config = readJsonConfig('config/pdca-defaults.json');
      assert.equal(typeof config.max_iterations, 'number');
      assert.ok(config.max_iterations > 0, 'max_iterations should be positive');
    });

    it('should have phase_timeout_ms field as a number', () => {
      config = readJsonConfig('config/pdca-defaults.json');
      assert.equal(typeof config.phase_timeout_ms, 'number');
      assert.ok(config.phase_timeout_ms > 0, 'phase_timeout_ms should be positive');
    });

    it('should have auto_act field as a boolean', () => {
      config = readJsonConfig('config/pdca-defaults.json');
      assert.equal(typeof config.auto_act, 'boolean');
    });

    it('should have default_agents with plan, do, check, act keys', () => {
      config = readJsonConfig('config/pdca-defaults.json');
      assert.ok(config.default_agents, 'should have default_agents');
      assert.ok(Array.isArray(config.default_agents.plan));
      assert.ok(Array.isArray(config.default_agents.do));
      assert.ok(Array.isArray(config.default_agents.check));
      assert.ok(Array.isArray(config.default_agents.act));
    });
  });

  describe('config/pipeline-phases.json', () => {
    let config;

    it('should be valid JSON', () => {
      config = readJsonConfig('config/pipeline-phases.json');
      assert.ok(config);
    });

    it('should have phases array', () => {
      config = readJsonConfig('config/pipeline-phases.json');
      assert.ok(Array.isArray(config.phases), 'should have phases array');
      assert.ok(config.phases.length > 0, 'phases should not be empty');
    });

    it('each phase should have index, name, agent, and gate fields', () => {
      config = readJsonConfig('config/pipeline-phases.json');
      for (const phase of config.phases) {
        assert.equal(typeof phase.index, 'number', `phase missing index`);
        assert.equal(typeof phase.name, 'string', `phase missing name`);
        assert.equal(typeof phase.agent, 'string', `phase missing agent`);
        assert.equal(typeof phase.gate, 'string', `phase missing gate`);
      }
    });

    it('should have presets object with full, standard, minimal, auto', () => {
      config = readJsonConfig('config/pipeline-phases.json');
      assert.ok(config.presets, 'should have presets object');
      assert.ok('full' in config.presets);
      assert.ok('standard' in config.presets);
      assert.ok('minimal' in config.presets);
      assert.ok('auto' in config.presets);
    });

    it('each preset should have phases (array or null) and description', () => {
      config = readJsonConfig('config/pipeline-phases.json');
      for (const [name, preset] of Object.entries(config.presets)) {
        // 'auto' preset has phases: null for auto-detection
        if (name === 'auto') {
          assert.equal(preset.phases, null, `preset ${name} should have phases: null for auto-detection`);
        } else {
          assert.ok(Array.isArray(preset.phases), `preset ${name} should have phases array`);
        }
        assert.equal(typeof preset.description, 'string', `preset ${name} should have description`);
      }
    });
  });

  describe('plugin.json', () => {
    let config;

    it('should be valid JSON', () => {
      config = readJsonConfig('plugin.json');
      assert.ok(config);
    });

    it('should have name field', () => {
      config = readJsonConfig('plugin.json');
      assert.equal(typeof config.name, 'string');
      assert.equal(config.name, 'blueprint');
    });

    it('should have version field', () => {
      config = readJsonConfig('plugin.json');
      assert.equal(typeof config.version, 'string');
      assert.match(config.version, /^\d+\.\d+\.\d+$/);
    });

    it('should have description field', () => {
      config = readJsonConfig('plugin.json');
      assert.equal(typeof config.description, 'string');
      assert.ok(config.description.length > 0);
    });

    it('should have skills field pointing to directory', () => {
      config = readJsonConfig('plugin.json');
      assert.equal(typeof config.skills, 'string');
    });
  });

  describe('.mcp.json', () => {
    it('should not exist (removed in v1.1.0 - MCP server registered via plugin.json)', () => {
      const mcpPath = join(projectRoot, '.mcp.json');
      assert.ok(!existsSync(mcpPath), '.mcp.json should not exist (removed in v1.1.0)');
    });
  });

  describe('hooks/hooks.json', () => {
    let config;

    it('should be valid JSON', () => {
      config = readJsonConfig('hooks/hooks.json');
      assert.ok(config);
    });

    it('should have hooks object', () => {
      config = readJsonConfig('hooks/hooks.json');
      assert.ok(config.hooks, 'should have hooks object');
      assert.equal(typeof config.hooks, 'object');
    });

    it('should have all expected event types', () => {
      config = readJsonConfig('hooks/hooks.json');
      const expectedEvents = [
        'UserPromptSubmit',
        'PostToolUse',
        'SessionStart',
        'PreCompact',
        'Stop',
        'SessionEnd'
      ];
      for (const event of expectedEvents) {
        assert.ok(
          event in config.hooks,
          `hooks should contain event type: ${event}`
        );
      }
    });

    it('each event should have at least one hook with matcher and hooks array', () => {
      config = readJsonConfig('hooks/hooks.json');
      for (const [eventName, entries] of Object.entries(config.hooks)) {
        assert.ok(Array.isArray(entries), `${eventName} should be an array`);
        assert.ok(entries.length > 0, `${eventName} should have at least one entry`);
        for (const entry of entries) {
          assert.equal(typeof entry.matcher, 'string', `${eventName} entry should have matcher`);
          assert.ok(Array.isArray(entry.hooks), `${eventName} entry should have hooks array`);
        }
      }
    });

    it('each hook command should reference a valid script file', () => {
      config = readJsonConfig('hooks/hooks.json');
      for (const [, entries] of Object.entries(config.hooks)) {
        for (const entry of entries) {
          for (const hook of entry.hooks) {
            assert.equal(hook.type, 'command', 'hook type should be command');
            assert.ok(hook.command.includes('node'), 'hook command should use node');
            assert.ok(
              hook.command.includes('${CLAUDE_PLUGIN_ROOT}'),
              'hook command should reference ${CLAUDE_PLUGIN_ROOT}'
            );
          }
        }
      }
    });
  });
});
