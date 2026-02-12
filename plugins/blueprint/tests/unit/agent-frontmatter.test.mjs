import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const agentsDir = join(__dirname, '..', '..', 'agents');

/**
 * Parse YAML frontmatter from a markdown file (between --- markers).
 * Simple parser -- no external YAML library needed.
 * Handles: key: value, key: value1, value2 (comma-separated)
 */
function parseFrontmatter(filePath) {
  const raw = readFileSync(filePath, 'utf-8');
  const match = raw.match(/^---\n([\s\S]*?)\n---/);
  if (!match) return null;

  const yaml = match[1];
  const result = {};

  for (const line of yaml.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;

    const colonIdx = trimmed.indexOf(':');
    if (colonIdx === -1) continue;

    const key = trimmed.slice(0, colonIdx).trim();
    const value = trimmed.slice(colonIdx + 1).trim();

    // Handle booleans
    if (value === 'true') { result[key] = true; continue; }
    if (value === 'false') { result[key] = false; continue; }

    // Handle numbers
    if (/^\d+$/.test(value)) { result[key] = parseInt(value, 10); continue; }

    result[key] = value;
  }

  return result;
}

// Fields that are NOT valid for agent markdown frontmatter
const INVALID_FIELDS = ['tools', 'permissionMode', 'maxTurns'];

describe('agent frontmatter validation', () => {

  describe('agents/gap-detector.md', () => {
    const filePath = join(agentsDir, 'gap-detector.md');
    let fm;

    it('should have valid YAML frontmatter', () => {
      fm = parseFrontmatter(filePath);
      assert.ok(fm, 'should have parseable frontmatter');
    });

    it('should have name field set to "gap-detector"', () => {
      fm = parseFrontmatter(filePath);
      assert.equal(fm.name, 'gap-detector');
    });

    it('should have description field', () => {
      fm = parseFrontmatter(filePath);
      assert.equal(typeof fm.description, 'string');
      assert.ok(fm.description.length > 0);
    });

    it('should have model set to opus', () => {
      fm = parseFrontmatter(filePath);
      assert.equal(fm.model, 'opus');
    });

    it('should have disallowedTools including Write and Edit', () => {
      fm = parseFrontmatter(filePath);
      assert.ok(fm.disallowedTools, 'should have disallowedTools');
      const tools = fm.disallowedTools.split(',').map(t => t.trim());
      assert.ok(tools.includes('Write'), 'disallowedTools should include Write');
      assert.ok(tools.includes('Edit'), 'disallowedTools should include Edit');
    });

    it('should NOT contain invalid fields', () => {
      fm = parseFrontmatter(filePath);
      for (const field of INVALID_FIELDS) {
        assert.ok(!(field in fm), `should not have invalid field: ${field}`);
      }
    });
  });

  describe('agents/design-writer.md', () => {
    const filePath = join(agentsDir, 'design-writer.md');
    let fm;

    it('should have valid YAML frontmatter', () => {
      fm = parseFrontmatter(filePath);
      assert.ok(fm, 'should have parseable frontmatter');
    });

    it('should have name field set to "design-writer"', () => {
      fm = parseFrontmatter(filePath);
      assert.equal(fm.name, 'design-writer');
    });

    it('should have description field', () => {
      fm = parseFrontmatter(filePath);
      assert.equal(typeof fm.description, 'string');
      assert.ok(fm.description.length > 0);
    });

    it('should have model set to sonnet', () => {
      fm = parseFrontmatter(filePath);
      assert.equal(fm.model, 'sonnet');
    });

    it('should NOT contain invalid fields', () => {
      fm = parseFrontmatter(filePath);
      for (const field of INVALID_FIELDS) {
        assert.ok(!(field in fm), `should not have invalid field: ${field}`);
      }
    });
  });

  describe('agents/pdca-iterator.md', () => {
    const filePath = join(agentsDir, 'pdca-iterator.md');
    let fm;

    it('should have valid YAML frontmatter', () => {
      fm = parseFrontmatter(filePath);
      assert.ok(fm, 'should have parseable frontmatter');
    });

    it('should have name field set to "pdca-iterator"', () => {
      fm = parseFrontmatter(filePath);
      assert.equal(fm.name, 'pdca-iterator');
    });

    it('should have description field', () => {
      fm = parseFrontmatter(filePath);
      assert.equal(typeof fm.description, 'string');
      assert.ok(fm.description.length > 0);
    });

    it('should have model set to sonnet', () => {
      fm = parseFrontmatter(filePath);
      assert.equal(fm.model, 'sonnet');
    });

    it('should NOT contain invalid fields', () => {
      fm = parseFrontmatter(filePath);
      for (const field of INVALID_FIELDS) {
        assert.ok(!(field in fm), `should not have invalid field: ${field}`);
      }
    });
  });
});
