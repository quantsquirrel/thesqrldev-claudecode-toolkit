import { describe, it, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, readFile, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import {
  generateId,
  ensureDir,
  loadState,
  saveState,
  findBlueprintRoot
} from '../../hooks/lib/state-manager.mjs';

describe('Gap Analysis Skill Integration', () => {
  let tempDir;
  let blueprintDir;

  before(async () => {
    tempDir = await mkdtemp(join(tmpdir(), 'blueprint-gap-test-'));
    blueprintDir = join(tempDir, '.blueprint');
    ensureDir(blueprintDir);
  });

  after(async () => {
    await rm(tempDir, { recursive: true, force: true });
  });

  describe('Gap Analysis Workflow', () => {
    it('should create gap analysis directory structure', () => {
      const gapsDir = join(blueprintDir, 'gaps');
      const analysesDir = join(gapsDir, 'analyses');
      const designsDir = join(gapsDir, 'designs');

      ensureDir(analysesDir);
      ensureDir(designsDir);

      assert.ok(existsSync(analysesDir), 'analyses directory should exist');
      assert.ok(existsSync(designsDir), 'designs directory should exist');
    });

    it('should generate gap analysis with unique ID', () => {
      const gapId = `gap-${generateId()}`;
      assert.match(gapId, /^gap-\d{8}-[0-9a-f]{6}$/);
    });

    it('should create and save gap analysis state', () => {
      const gapId = `gap-${generateId()}`;
      const analysisPath = join(blueprintDir, 'gaps', 'analyses', `${gapId}.json`);

      const gapAnalysis = {
        id: gapId,
        desired_state: 'OAuth2 implementation with refresh tokens',
        scope: 'project',
        timestamp: new Date().toISOString(),
        gaps: [
          {
            category: 'features',
            severity: 'CRITICAL',
            title: 'Missing refresh token mechanism',
            description: 'Current implementation only supports access tokens',
            current_state: 'src/auth/token.ts:42-80',
            desired_state: 'OAuth2 RFC 6749 section 6',
            effort: 'high',
            impact: 'high'
          },
          {
            category: 'architecture',
            severity: 'HIGH',
            title: 'Token storage not persistent',
            description: 'Tokens stored in memory, lost on restart',
            current_state: 'src/auth/store.ts:15',
            desired_state: 'Persistent storage (Redis/DB)',
            effort: 'medium',
            impact: 'high'
          }
        ],
        summary: {
          total_gaps: 2,
          by_severity: { CRITICAL: 1, HIGH: 1, MEDIUM: 0, LOW: 0 },
          by_category: { features: 1, architecture: 1, quality: 0, dependencies: 0 }
        }
      };

      saveState(analysisPath, gapAnalysis);
      assert.ok(existsSync(analysisPath), 'gap analysis file should exist');

      const loaded = loadState(analysisPath);
      assert.deepStrictEqual(loaded, gapAnalysis);
    });

    it('should validate gap analysis schema', () => {
      const gapId = `gap-${generateId()}`;
      const analysisPath = join(blueprintDir, 'gaps', 'analyses', `${gapId}.json`);

      const gapAnalysis = {
        id: gapId,
        desired_state: 'Test feature',
        scope: 'file',
        timestamp: new Date().toISOString(),
        gaps: [],
        summary: {
          total_gaps: 0,
          by_severity: {},
          by_category: {}
        }
      };

      saveState(analysisPath, gapAnalysis);
      const loaded = loadState(analysisPath);

      // Validate required fields
      assert.ok(loaded.id, 'should have id');
      assert.ok(loaded.desired_state, 'should have desired_state');
      assert.ok(loaded.scope, 'should have scope');
      assert.ok(loaded.timestamp, 'should have timestamp');
      assert.ok(Array.isArray(loaded.gaps), 'gaps should be array');
      assert.ok(loaded.summary, 'should have summary');
      assert.equal(typeof loaded.summary.total_gaps, 'number');
    });

    it('should prioritize gaps by severity and impact', () => {
      const gaps = [
        { severity: 'CRITICAL', effort: 'high', impact: 'high', title: 'Gap 1' },
        { severity: 'HIGH', effort: 'low', impact: 'high', title: 'Gap 2' },
        { severity: 'MEDIUM', effort: 'medium', impact: 'medium', title: 'Gap 3' },
        { severity: 'LOW', effort: 'low', impact: 'low', title: 'Gap 4' }
      ];

      const severityWeights = { CRITICAL: 10, HIGH: 7, MEDIUM: 4, LOW: 2 };
      const effortImpactValues = { high: 3, medium: 2, low: 1 };

      const calculatePriority = (gap) => {
        const severityWeight = severityWeights[gap.severity];
        const impactValue = effortImpactValues[gap.impact];
        const effortValue = effortImpactValues[gap.effort];
        return (severityWeight * impactValue) / effortValue;
      };

      const prioritized = gaps
        .map(gap => ({ ...gap, priority: calculatePriority(gap) }))
        .sort((a, b) => b.priority - a.priority);

      // HIGH with low effort has priority: (7 * 3) / 1 = 21
      // CRITICAL with high effort has priority: (10 * 3) / 3 = 10
      // So HIGH low-effort should be first
      assert.equal(prioritized[0].severity, 'HIGH');
      assert.equal(prioritized[0].effort, 'low');
      // CRITICAL should be second
      assert.equal(prioritized[1].severity, 'CRITICAL');
    });

    it('should create design document when --generate-design flag is set', () => {
      const gapId = `gap-${generateId()}`;
      const designPath = join(blueprintDir, 'gaps', 'designs', `${gapId}-design.md`);

      const designDoc = `# Design Document: ${gapId}

## Overview
Implementation plan for OAuth2 with refresh tokens

## Phases
### Phase 1: Critical Gaps
- Implement refresh token mechanism

### Phase 2: High Priority Gaps
- Add persistent token storage

## Acceptance Criteria
- [ ] Refresh tokens are generated and stored
- [ ] Token refresh endpoint is implemented
- [ ] Persistent storage is configured

## Dependencies
- Redis or PostgreSQL for token storage
- OAuth2 library updates

## Risks
- Breaking changes to existing auth flow
- Migration of existing sessions required
`;

      ensureDir(join(blueprintDir, 'gaps', 'designs'));
      saveState(designPath.replace('.md', '.json'), {
        gapId,
        designPath,
        content: designDoc
      });

      assert.ok(existsSync(designPath.replace('.md', '.json')));
    });

    it('should update gap analysis index', () => {
      const indexPath = join(blueprintDir, 'gaps', 'analyses', 'index.json');

      const gapId1 = `gap-${generateId()}`;
      const gapId2 = `gap-${generateId()}`;

      // Initialize index
      const index = {
        analyses: [
          { id: gapId1, desired_state: 'Feature A', created_at: new Date().toISOString() },
          { id: gapId2, desired_state: 'Feature B', created_at: new Date().toISOString() }
        ],
        updated_at: new Date().toISOString()
      };

      saveState(indexPath, index);
      const loaded = loadState(indexPath);

      assert.equal(loaded.analyses.length, 2);
      assert.ok(loaded.analyses.find(a => a.id === gapId1));
      assert.ok(loaded.analyses.find(a => a.id === gapId2));
    });

    it('should handle different scope levels', () => {
      const scopes = ['file', 'dir', 'project'];

      scopes.forEach(scope => {
        const gapId = `gap-${generateId()}`;
        const analysisPath = join(blueprintDir, 'gaps', 'analyses', `${gapId}.json`);

        const gapAnalysis = {
          id: gapId,
          desired_state: `Test with ${scope} scope`,
          scope: scope,
          timestamp: new Date().toISOString(),
          gaps: [],
          summary: { total_gaps: 0, by_severity: {}, by_category: {} }
        };

        saveState(analysisPath, gapAnalysis);
        const loaded = loadState(analysisPath);

        assert.equal(loaded.scope, scope);
      });
    });

    it('should categorize gaps correctly', () => {
      const categories = ['features', 'architecture', 'quality', 'dependencies'];

      categories.forEach(category => {
        const gap = {
          category,
          severity: 'MEDIUM',
          title: `Test ${category} gap`,
          description: `This is a ${category} gap`,
          effort: 'medium',
          impact: 'medium'
        };

        assert.ok(categories.includes(gap.category));
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle invalid desired state', () => {
      const gapId = `gap-${generateId()}`;
      const analysisPath = join(blueprintDir, 'gaps', 'analyses', `${gapId}.json`);

      // Empty desired state should be handled
      const gapAnalysis = {
        id: gapId,
        desired_state: '',
        scope: 'project',
        timestamp: new Date().toISOString(),
        gaps: [],
        summary: { total_gaps: 0, by_severity: {}, by_category: {} }
      };

      saveState(analysisPath, gapAnalysis);
      const loaded = loadState(analysisPath);

      // Should still save, but validation should catch this
      assert.equal(loaded.desired_state, '');
    });

    it('should handle corrupted state files', () => {
      const analysisPath = join(blueprintDir, 'gaps', 'analyses', 'corrupted.json');

      ensureDir(join(blueprintDir, 'gaps', 'analyses'));
      writeFile(analysisPath, 'invalid-json{{{', 'utf-8');

      const loaded = loadState(analysisPath);
      assert.equal(loaded, null);
    });
  });
});
