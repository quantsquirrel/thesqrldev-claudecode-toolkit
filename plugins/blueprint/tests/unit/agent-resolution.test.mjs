import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, extname } from 'node:path';

const PROJECT_ROOT = join(import.meta.dirname, '..', '..');

/**
 * Recursively collect all source files (excluding .omc/, .claude/, node_modules/, .git/).
 */
function collectSourceFiles(dir, files = []) {
  const entries = readdirSync(dir);
  for (const entry of entries) {
    const fullPath = join(dir, entry);
    // Skip non-source directories
    if (['.omc', '.claude', 'node_modules', '.git', '.blueprint'].includes(entry)) continue;
    const stats = statSync(fullPath);
    if (stats.isDirectory()) {
      collectSourceFiles(fullPath, files);
    } else {
      const ext = extname(entry);
      if (['.mjs', '.cjs', '.js', '.json', '.md'].includes(ext)) {
        files.push(fullPath);
      }
    }
  }
  return files;
}

describe('Agent Resolution - OMC Independence', () => {
  const sourceFiles = collectSourceFiles(PROJECT_ROOT);

  it('should have collected source files for analysis', () => {
    assert.ok(sourceFiles.length > 0, `Expected source files, found ${sourceFiles.length}`);
  });

  it('should not reference oh-my-claudecode in any source file', () => {
    const ALLOWED_FILES = new Set(['CHANGELOG.md', 'agent-resolution.test.mjs', 'AGENTS.md']);
    const violations = [];
    for (const filePath of sourceFiles) {
      const relativePath = filePath.replace(PROJECT_ROOT + '/', '');
      const fileName = relativePath.split('/').pop();
      // Skip files that legitimately mention OMC (changelog history, this test, READMEs, AGENTS.md)
      if (ALLOWED_FILES.has(fileName)) continue;
      if (relativePath.startsWith('README')) continue;
      const content = readFileSync(filePath, 'utf-8');
      const lines = content.split('\n');
      for (let i = 0; i < lines.length; i++) {
        if (lines[i].includes('oh-my-claudecode')) {
          violations.push(`${relativePath}:${i + 1}: ${lines[i].trim()}`);
        }
      }
    }
    assert.equal(violations.length, 0,
      `Found ${violations.length} oh-my-claudecode reference(s) in source:\n${violations.join('\n')}`);
  });

  it('should not reference .omc/blueprint/ state path in any source file', () => {
    const ALLOWED_FILES = new Set(['CHANGELOG.md', 'agent-resolution.test.mjs', 'AGENTS.md']);
    const violations = [];
    for (const filePath of sourceFiles) {
      const relativePath = filePath.replace(PROJECT_ROOT + '/', '');
      const fileName = relativePath.split('/').pop();
      if (ALLOWED_FILES.has(fileName)) continue;
      const content = readFileSync(filePath, 'utf-8');
      const lines = content.split('\n');
      for (let i = 0; i < lines.length; i++) {
        if (lines[i].includes('.omc/blueprint')) {
          violations.push(`${relativePath}:${i + 1}: ${lines[i].trim()}`);
        }
      }
    }
    assert.equal(violations.length, 0,
      `Found ${violations.length} .omc/blueprint/ reference(s):\n${violations.join('\n')}`);
  });

  it('should use blueprint: namespace for all agent references in SKILL.md files', () => {
    const skillFiles = sourceFiles.filter(f => f.endsWith('SKILL.md'));
    assert.ok(skillFiles.length >= 3, `Expected at least 3 SKILL.md files, found ${skillFiles.length}`);

    for (const filePath of skillFiles) {
      const content = readFileSync(filePath, 'utf-8');
      const agentRefs = content.match(/subagent_type="([^"]+)"/g) || [];
      for (const ref of agentRefs) {
        const agentName = ref.match(/subagent_type="([^"]+)"/)[1];
        assert.ok(agentName.startsWith('blueprint:'),
          `${filePath}: Agent reference "${agentName}" should use blueprint: namespace`);
      }
    }
  });

  it('should use .blueprint/ state path in SKILL.md files', () => {
    const skillFiles = sourceFiles.filter(f => f.endsWith('SKILL.md'));
    for (const filePath of skillFiles) {
      const content = readFileSync(filePath, 'utf-8');
      // If the file references state paths, they should use .blueprint/
      if (content.includes('state file') || content.includes('State file')) {
        assert.ok(content.includes('.blueprint/'),
          `${filePath}: Should reference .blueprint/ for state paths`);
      }
    }
  });

  it('should have all 9 agents in the agents/ directory', () => {
    const agentsDir = join(PROJECT_ROOT, 'agents');
    const agentFiles = readdirSync(agentsDir).filter(f => f.endsWith('.md') && f !== 'AGENTS.md');
    const expectedAgents = [
      'analyst.md', 'architect.md', 'design-writer.md', 'executor.md',
      'gap-detector.md', 'pdca-iterator.md', 'reviewer.md', 'tester.md', 'verifier.md'
    ];
    assert.deepStrictEqual(agentFiles.sort(), expectedAgents.sort(),
      'Missing or extra agents in agents/ directory');
  });

  it('should use blueprint: namespace in pipeline-phases.json', () => {
    const configPath = join(PROJECT_ROOT, 'config', 'pipeline-phases.json');
    const config = JSON.parse(readFileSync(configPath, 'utf-8'));
    for (const phase of config.phases) {
      assert.ok(phase.agent.startsWith('blueprint:'),
        `Phase "${phase.name}" agent "${phase.agent}" should use blueprint: namespace`);
    }
  });

  it('should have findBlueprintRoot (not findOmcRoot) in source files', () => {
    const jsFiles = sourceFiles.filter(f =>
      ['.mjs', '.cjs', '.js'].includes(extname(f)) &&
      !f.includes('agent-resolution.test.mjs')
    );
    for (const filePath of jsFiles) {
      const content = readFileSync(filePath, 'utf-8');
      assert.ok(!content.includes('findOmcRoot'),
        `${filePath}: Should not contain findOmcRoot (use findBlueprintRoot)`);
    }
  });
});
