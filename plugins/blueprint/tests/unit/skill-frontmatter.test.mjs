import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const skillsDir = join(__dirname, '..', '..', 'skills');

/**
 * Parse YAML frontmatter from a markdown file (between --- markers).
 * Simple parser -- no external YAML library needed.
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
    let value = trimmed.slice(colonIdx + 1).trim();

    // Strip surrounding quotes if present
    if ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }

    // Handle booleans
    if (value === 'true') { result[key] = true; continue; }
    if (value === 'false') { result[key] = false; continue; }

    // Handle numbers
    if (/^\d+$/.test(value)) { result[key] = parseInt(value, 10); continue; }

    result[key] = value;
  }

  return result;
}

// Skills to test
const SKILLS = [
  { dir: 'pdca', expectedName: 'pdca' },
  { dir: 'gap', expectedName: 'gap' },
  { dir: 'pipeline', expectedName: 'pipeline' },
  { dir: 'cancel', expectedName: 'cancel' }
];

describe('skill frontmatter validation', () => {

  for (const skill of SKILLS) {
    describe(`skills/${skill.dir}/SKILL.md`, () => {
      const filePath = join(skillsDir, skill.dir, 'SKILL.md');
      let fm;

      it('should have valid YAML frontmatter', () => {
        fm = parseFrontmatter(filePath);
        assert.ok(fm, 'should have parseable frontmatter');
      });

      it(`should have name field set to "${skill.expectedName}"`, () => {
        fm = parseFrontmatter(filePath);
        assert.equal(fm.name, skill.expectedName);
      });

      it('should have description field with actionable text', () => {
        fm = parseFrontmatter(filePath);
        assert.equal(typeof fm.description, 'string');
        assert.ok(fm.description.length > 10, 'description should be meaningful (>10 chars)');
      });

      it('should have allowed-tools field', () => {
        fm = parseFrontmatter(filePath);
        assert.ok(fm['allowed-tools'], 'should have allowed-tools');
        assert.equal(typeof fm['allowed-tools'], 'string');
        assert.ok(fm['allowed-tools'].length > 0);
      });

      it('should have user-invocable set to true', () => {
        fm = parseFrontmatter(filePath);
        assert.equal(fm['user-invocable'], true);
      });
    });
  }
});
