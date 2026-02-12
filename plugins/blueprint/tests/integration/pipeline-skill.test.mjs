import { describe, it, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import {
  generateId,
  ensureDir,
  loadState,
  saveState,
  archiveState
} from '../../hooks/lib/state-manager.mjs';

describe('Pipeline Skill Integration', () => {
  let tempDir;
  let blueprintDir;

  before(async () => {
    tempDir = await mkdtemp(join(tmpdir(), 'blueprint-pipeline-test-'));
    blueprintDir = join(tempDir, '.blueprint');
    ensureDir(blueprintDir);
  });

  after(async () => {
    await rm(tempDir, { recursive: true, force: true });
  });

  describe('Pipeline Workflow', () => {
    it('should create pipeline directory structure', () => {
      const pipelineDir = join(blueprintDir, 'pipeline');
      const runsDir = join(pipelineDir, 'runs');
      const historyDir = join(pipelineDir, 'history');

      ensureDir(runsDir);
      ensureDir(historyDir);

      assert.ok(existsSync(runsDir), 'runs directory should exist');
      assert.ok(existsSync(historyDir), 'history directory should exist');
    });

    it('should initialize pipeline run with full preset', () => {
      const pipelineId = `pipeline-${generateId()}`;
      const runPath = join(blueprintDir, 'pipeline', 'runs', `${pipelineId}.json`);

      const pipelineRun = {
        id: pipelineId,
        feature: 'user authentication with JWT',
        preset: 'full',
        status: 'running',
        current_phase: 1,
        total_phases: 9,
        on_error: 'pause',
        created_at: new Date().toISOString(),
        phases: [
          { number: 1, name: 'requirements', agent: 'analyst', status: 'running', output: null, retries: 0 },
          { number: 2, name: 'architecture', agent: 'architect', status: 'pending', output: null, retries: 0 },
          { number: 3, name: 'design', agent: 'design-writer', status: 'pending', output: null, retries: 0 },
          { number: 4, name: 'implementation', agent: 'executor', status: 'pending', output: null, retries: 0 },
          { number: 5, name: 'unit-tests', agent: 'test-engineer', status: 'pending', output: null, retries: 0 },
          { number: 6, name: 'integration-tests', agent: 'test-engineer', status: 'pending', output: null, retries: 0 },
          { number: 7, name: 'code-review', agent: 'code-reviewer', status: 'pending', output: null, retries: 0 },
          { number: 8, name: 'gap-analysis', agent: 'gap-detector', status: 'pending', output: null, retries: 0 },
          { number: 9, name: 'verification', agent: 'verifier', status: 'pending', output: null, retries: 0 }
        ]
      };

      saveState(runPath, pipelineRun);
      assert.ok(existsSync(runPath));

      const loaded = loadState(runPath);
      assert.deepStrictEqual(loaded, pipelineRun);
    });

    it('should initialize pipeline run with standard preset', () => {
      const pipelineId = `pipeline-${generateId()}`;
      const runPath = join(blueprintDir, 'pipeline', 'runs', `${pipelineId}.json`);

      const pipelineRun = {
        id: pipelineId,
        feature: 'user dashboard',
        preset: 'standard',
        status: 'running',
        current_phase: 1,
        total_phases: 6,
        on_error: 'pause',
        created_at: new Date().toISOString(),
        phases: [
          { number: 1, name: 'requirements', agent: 'analyst', status: 'running', output: null, retries: 0 },
          { number: 2, name: 'design', agent: 'design-writer', status: 'pending', output: null, retries: 0 },
          { number: 3, name: 'implementation', agent: 'executor', status: 'pending', output: null, retries: 0 },
          { number: 4, name: 'unit-tests', agent: 'test-engineer', status: 'pending', output: null, retries: 0 },
          { number: 5, name: 'code-review', agent: 'code-reviewer', status: 'pending', output: null, retries: 0 },
          { number: 6, name: 'verification', agent: 'verifier', status: 'pending', output: null, retries: 0 }
        ]
      };

      saveState(runPath, pipelineRun);
      const loaded = loadState(runPath);

      assert.equal(loaded.preset, 'standard');
      assert.equal(loaded.total_phases, 6);
    });

    it('should initialize pipeline run with minimal preset', () => {
      const pipelineId = `pipeline-${generateId()}`;
      const runPath = join(blueprintDir, 'pipeline', 'runs', `${pipelineId}.json`);

      const pipelineRun = {
        id: pipelineId,
        feature: 'bug fix',
        preset: 'minimal',
        status: 'running',
        current_phase: 1,
        total_phases: 3,
        on_error: 'pause',
        created_at: new Date().toISOString(),
        phases: [
          { number: 1, name: 'design', agent: 'design-writer', status: 'running', output: null, retries: 0 },
          { number: 2, name: 'implementation', agent: 'executor', status: 'pending', output: null, retries: 0 },
          { number: 3, name: 'verification', agent: 'verifier', status: 'pending', output: null, retries: 0 }
        ]
      };

      saveState(runPath, pipelineRun);
      const loaded = loadState(runPath);

      assert.equal(loaded.preset, 'minimal');
      assert.equal(loaded.total_phases, 3);
    });

    it('should progress through phases sequentially', () => {
      const pipelineId = `pipeline-${generateId()}`;
      const runPath = join(blueprintDir, 'pipeline', 'runs', `${pipelineId}.json`);

      const pipelineRun = {
        id: pipelineId,
        feature: 'test feature',
        preset: 'minimal',
        status: 'running',
        current_phase: 1,
        total_phases: 3,
        on_error: 'pause',
        created_at: new Date().toISOString(),
        phases: [
          { number: 1, name: 'design', agent: 'design-writer', status: 'running', output: null, retries: 0 },
          { number: 2, name: 'implementation', agent: 'executor', status: 'pending', output: null, retries: 0 },
          { number: 3, name: 'verification', agent: 'verifier', status: 'pending', output: null, retries: 0 }
        ]
      };

      saveState(runPath, pipelineRun);

      // Complete phase 1
      pipelineRun.phases[0].status = 'completed';
      pipelineRun.phases[0].output = 'Design completed';
      pipelineRun.current_phase = 2;
      pipelineRun.phases[1].status = 'running';
      saveState(runPath, pipelineRun);

      let loaded = loadState(runPath);
      assert.equal(loaded.phases[0].status, 'completed');
      assert.equal(loaded.current_phase, 2);
      assert.equal(loaded.phases[1].status, 'running');

      // Complete phase 2
      pipelineRun.phases[1].status = 'completed';
      pipelineRun.phases[1].output = 'Implementation completed';
      pipelineRun.current_phase = 3;
      pipelineRun.phases[2].status = 'running';
      saveState(runPath, pipelineRun);

      loaded = loadState(runPath);
      assert.equal(loaded.phases[1].status, 'completed');
      assert.equal(loaded.current_phase, 3);
    });

    it('should handle phase retry logic', () => {
      const pipelineId = `pipeline-${generateId()}`;
      const runPath = join(blueprintDir, 'pipeline', 'runs', `${pipelineId}.json`);

      const pipelineRun = {
        id: pipelineId,
        feature: 'test feature',
        preset: 'minimal',
        status: 'running',
        current_phase: 1,
        total_phases: 3,
        on_error: 'pause',
        created_at: new Date().toISOString(),
        phases: [
          { number: 1, name: 'design', agent: 'design-writer', status: 'running', output: null, retries: 0 },
          { number: 2, name: 'implementation', agent: 'executor', status: 'pending', output: null, retries: 0 },
          { number: 3, name: 'verification', agent: 'verifier', status: 'pending', output: null, retries: 0 }
        ]
      };

      saveState(runPath, pipelineRun);

      // Phase 1 fails
      pipelineRun.phases[0].status = 'failed';
      pipelineRun.phases[0].retries = 1;
      saveState(runPath, pipelineRun);

      let loaded = loadState(runPath);
      assert.equal(loaded.phases[0].status, 'failed');
      assert.equal(loaded.phases[0].retries, 1);

      // Retry phase 1 (retries < 2 allowed)
      pipelineRun.phases[0].status = 'running';
      saveState(runPath, pipelineRun);

      loaded = loadState(runPath);
      assert.equal(loaded.phases[0].status, 'running');
      assert.ok(loaded.phases[0].retries < 2, 'should allow retry when retries < 2');
    });

    it('should enforce max retries per phase', () => {
      const pipelineId = `pipeline-${generateId()}`;
      const runPath = join(blueprintDir, 'pipeline', 'runs', `${pipelineId}.json`);

      const pipelineRun = {
        id: pipelineId,
        feature: 'test feature',
        preset: 'minimal',
        status: 'running',
        current_phase: 1,
        total_phases: 3,
        on_error: 'abort',
        created_at: new Date().toISOString(),
        phases: [
          { number: 1, name: 'design', agent: 'design-writer', status: 'failed', output: null, retries: 2 },
          { number: 2, name: 'implementation', agent: 'executor', status: 'pending', output: null, retries: 0 },
          { number: 3, name: 'verification', agent: 'verifier', status: 'pending', output: null, retries: 0 }
        ]
      };

      saveState(runPath, pipelineRun);
      const loaded = loadState(runPath);

      // Max retries reached, should not retry again
      assert.equal(loaded.phases[0].retries, 2);
      assert.ok(loaded.phases[0].retries >= 2, 'max retries reached');
    });

    it('should handle on_error=abort', () => {
      const pipelineId = `pipeline-${generateId()}`;
      const runPath = join(blueprintDir, 'pipeline', 'runs', `${pipelineId}.json`);

      const pipelineRun = {
        id: pipelineId,
        feature: 'test feature',
        preset: 'minimal',
        status: 'running',
        current_phase: 1,
        total_phases: 3,
        on_error: 'abort',
        created_at: new Date().toISOString(),
        phases: [
          { number: 1, name: 'design', agent: 'design-writer', status: 'running', output: null, retries: 0 },
          { number: 2, name: 'implementation', agent: 'executor', status: 'pending', output: null, retries: 0 },
          { number: 3, name: 'verification', agent: 'verifier', status: 'pending', output: null, retries: 0 }
        ]
      };

      saveState(runPath, pipelineRun);

      // Phase fails with abort mode
      pipelineRun.phases[0].status = 'failed';
      pipelineRun.status = 'failed';
      saveState(runPath, pipelineRun);

      const loaded = loadState(runPath);
      assert.equal(loaded.status, 'failed');
      assert.equal(loaded.on_error, 'abort');
    });

    it('should handle on_error=skip', () => {
      const pipelineId = `pipeline-${generateId()}`;
      const runPath = join(blueprintDir, 'pipeline', 'runs', `${pipelineId}.json`);

      const pipelineRun = {
        id: pipelineId,
        feature: 'test feature',
        preset: 'minimal',
        status: 'running',
        current_phase: 1,
        total_phases: 3,
        on_error: 'skip',
        created_at: new Date().toISOString(),
        phases: [
          { number: 1, name: 'design', agent: 'design-writer', status: 'running', output: null, retries: 0 },
          { number: 2, name: 'implementation', agent: 'executor', status: 'pending', output: null, retries: 0 },
          { number: 3, name: 'verification', agent: 'verifier', status: 'pending', output: null, retries: 0 }
        ]
      };

      saveState(runPath, pipelineRun);

      // Phase fails with skip mode
      pipelineRun.phases[0].status = 'skipped';
      pipelineRun.current_phase = 2;
      pipelineRun.phases[1].status = 'running';
      saveState(runPath, pipelineRun);

      const loaded = loadState(runPath);
      assert.equal(loaded.phases[0].status, 'skipped');
      assert.equal(loaded.current_phase, 2);
      assert.equal(loaded.on_error, 'skip');
    });

    it('should handle on_error=pause', () => {
      const pipelineId = `pipeline-${generateId()}`;
      const runPath = join(blueprintDir, 'pipeline', 'runs', `${pipelineId}.json`);

      const pipelineRun = {
        id: pipelineId,
        feature: 'test feature',
        preset: 'minimal',
        status: 'running',
        current_phase: 1,
        total_phases: 3,
        on_error: 'pause',
        created_at: new Date().toISOString(),
        phases: [
          { number: 1, name: 'design', agent: 'design-writer', status: 'running', output: null, retries: 0 },
          { number: 2, name: 'implementation', agent: 'executor', status: 'pending', output: null, retries: 0 },
          { number: 3, name: 'verification', agent: 'verifier', status: 'pending', output: null, retries: 0 }
        ]
      };

      saveState(runPath, pipelineRun);

      // Phase fails with pause mode
      pipelineRun.phases[0].status = 'failed';
      pipelineRun.status = 'paused';
      saveState(runPath, pipelineRun);

      const loaded = loadState(runPath);
      assert.equal(loaded.status, 'paused');
      assert.equal(loaded.on_error, 'pause');
    });

    it('should support --resume for paused pipelines', () => {
      const pipelineId = `pipeline-${generateId()}`;
      const runPath = join(blueprintDir, 'pipeline', 'runs', `${pipelineId}.json`);

      const pipelineRun = {
        id: pipelineId,
        feature: 'test feature',
        preset: 'minimal',
        status: 'paused',
        current_phase: 2,
        total_phases: 3,
        on_error: 'pause',
        created_at: new Date().toISOString(),
        phases: [
          { number: 1, name: 'design', agent: 'design-writer', status: 'completed', output: 'Done', retries: 0 },
          { number: 2, name: 'implementation', agent: 'executor', status: 'failed', output: null, retries: 1 },
          { number: 3, name: 'verification', agent: 'verifier', status: 'pending', output: null, retries: 0 }
        ]
      };

      saveState(runPath, pipelineRun);

      // Resume from paused state
      pipelineRun.status = 'running';
      pipelineRun.phases[1].status = 'running';
      saveState(runPath, pipelineRun);

      const loaded = loadState(runPath);
      assert.equal(loaded.status, 'running');
      assert.equal(loaded.current_phase, 2);
    });

    it('should support --start-phase to resume from specific phase', () => {
      const pipelineId = `pipeline-${generateId()}`;
      const runPath = join(blueprintDir, 'pipeline', 'runs', `${pipelineId}.json`);

      const pipelineRun = {
        id: pipelineId,
        feature: 'test feature',
        preset: 'standard',
        status: 'running',
        current_phase: 3, // Starting from phase 3
        total_phases: 6,
        on_error: 'pause',
        created_at: new Date().toISOString(),
        phases: [
          { number: 1, name: 'requirements', agent: 'analyst', status: 'completed', output: 'Done', retries: 0 },
          { number: 2, name: 'design', agent: 'design-writer', status: 'completed', output: 'Done', retries: 0 },
          { number: 3, name: 'implementation', agent: 'executor', status: 'running', output: null, retries: 0 },
          { number: 4, name: 'unit-tests', agent: 'test-engineer', status: 'pending', output: null, retries: 0 },
          { number: 5, name: 'code-review', agent: 'code-reviewer', status: 'pending', output: null, retries: 0 },
          { number: 6, name: 'verification', agent: 'verifier', status: 'pending', output: null, retries: 0 }
        ]
      };

      saveState(runPath, pipelineRun);
      const loaded = loadState(runPath);

      assert.equal(loaded.current_phase, 3);
      assert.equal(loaded.phases[0].status, 'completed');
      assert.equal(loaded.phases[1].status, 'completed');
      assert.equal(loaded.phases[2].status, 'running');
    });

    it('should complete pipeline when all phases done', () => {
      const pipelineId = `pipeline-${generateId()}`;
      const runPath = join(blueprintDir, 'pipeline', 'runs', `${pipelineId}.json`);

      const pipelineRun = {
        id: pipelineId,
        feature: 'test feature',
        preset: 'minimal',
        status: 'running',
        current_phase: 3,
        total_phases: 3,
        on_error: 'pause',
        created_at: new Date().toISOString(),
        phases: [
          { number: 1, name: 'design', agent: 'design-writer', status: 'completed', output: 'Done', retries: 0 },
          { number: 2, name: 'implementation', agent: 'executor', status: 'completed', output: 'Done', retries: 0 },
          { number: 3, name: 'verification', agent: 'verifier', status: 'completed', output: 'Done', retries: 0 }
        ]
      };

      // Mark as completed
      pipelineRun.status = 'completed';
      pipelineRun.completed_at = new Date().toISOString();

      saveState(runPath, pipelineRun);
      const loaded = loadState(runPath);

      assert.equal(loaded.status, 'completed');
      assert.ok(loaded.completed_at);
    });

    it('should archive completed pipeline to history', () => {
      const pipelineId = `pipeline-${generateId()}`;
      const runPath = join(blueprintDir, 'pipeline', 'runs', `${pipelineId}.json`);
      const historyDir = join(blueprintDir, 'pipeline', 'history');

      const pipelineRun = {
        id: pipelineId,
        feature: 'completed feature',
        preset: 'minimal',
        status: 'completed',
        current_phase: 3,
        total_phases: 3,
        on_error: 'pause',
        created_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        phases: []
      };

      saveState(runPath, pipelineRun);
      assert.ok(existsSync(runPath));

      // Archive
      const archivePath = archiveState(runPath, historyDir);

      assert.ok(!existsSync(runPath), 'original should be removed');
      assert.ok(existsSync(archivePath), 'archive should exist');

      const archived = loadState(archivePath);
      assert.equal(archived.id, pipelineId);
      assert.equal(archived.status, 'completed');
    });
  });

  describe('Error Handling', () => {
    it('should handle invalid preset', () => {
      const pipelineId = `pipeline-${generateId()}`;
      const runPath = join(blueprintDir, 'pipeline', 'runs', `${pipelineId}.json`);

      const pipelineRun = {
        id: pipelineId,
        feature: 'test feature',
        preset: 'invalid-preset', // Invalid preset
        status: 'running',
        current_phase: 1,
        total_phases: 3,
        on_error: 'pause',
        created_at: new Date().toISOString(),
        phases: []
      };

      saveState(runPath, pipelineRun);
      const loaded = loadState(runPath);

      // Validation should catch invalid preset
      const validPresets = ['full', 'standard', 'minimal', 'auto'];
      assert.ok(!validPresets.includes(loaded.preset));
    });

    it('should handle corrupted pipeline state', () => {
      const runPath = join(blueprintDir, 'pipeline', 'runs', 'corrupted.json');

      ensureDir(join(blueprintDir, 'pipeline', 'runs'));
      saveState(runPath, { invalid: 'data' });

      const loaded = loadState(runPath);
      assert.ok(loaded);
      assert.ok(!loaded.id);
    });
  });
});
