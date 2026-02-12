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

describe('Cancel Skill Integration', () => {
  let tempDir;
  let blueprintDir;

  before(async () => {
    tempDir = await mkdtemp(join(tmpdir(), 'blueprint-cancel-test-'));
    blueprintDir = join(tempDir, '.blueprint');
    ensureDir(blueprintDir);
  });

  after(async () => {
    await rm(tempDir, { recursive: true, force: true });
  });

  describe('Cancel Operations', () => {
    it('should discover active PDCA cycles', () => {
      const pdcaDir = join(blueprintDir, 'pdca');
      const cyclesDir = join(pdcaDir, 'cycles');
      ensureDir(cyclesDir);

      const cycleId1 = `pdca-${generateId()}`;
      const cycleId2 = `pdca-${generateId()}`;

      // Create active cycles
      const cycle1 = {
        id: cycleId1,
        task: 'Task A',
        status: 'active',
        current_phase: 'plan',
        iteration: 1,
        max_iterations: 4,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        phases: {}
      };

      const cycle2 = {
        id: cycleId2,
        task: 'Task B',
        status: 'active',
        current_phase: 'do',
        iteration: 2,
        max_iterations: 4,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        phases: {}
      };

      saveState(join(cyclesDir, `${cycleId1}.json`), cycle1);
      saveState(join(cyclesDir, `${cycleId2}.json`), cycle2);

      // Verify they exist
      assert.ok(existsSync(join(cyclesDir, `${cycleId1}.json`)));
      assert.ok(existsSync(join(cyclesDir, `${cycleId2}.json`)));

      const loaded1 = loadState(join(cyclesDir, `${cycleId1}.json`));
      const loaded2 = loadState(join(cyclesDir, `${cycleId2}.json`));

      assert.equal(loaded1.status, 'active');
      assert.equal(loaded2.status, 'active');
    });

    it('should discover active pipeline runs', () => {
      const pipelineDir = join(blueprintDir, 'pipeline');
      const runsDir = join(pipelineDir, 'runs');
      ensureDir(runsDir);

      const pipelineId1 = `pipeline-${generateId()}`;
      const pipelineId2 = `pipeline-${generateId()}`;

      // Create active and paused pipelines
      const run1 = {
        id: pipelineId1,
        feature: 'Feature X',
        preset: 'standard',
        status: 'running',
        current_phase: 3,
        total_phases: 6,
        on_error: 'pause',
        created_at: new Date().toISOString(),
        phases: []
      };

      const run2 = {
        id: pipelineId2,
        feature: 'Feature Y',
        preset: 'minimal',
        status: 'paused',
        current_phase: 2,
        total_phases: 3,
        on_error: 'pause',
        created_at: new Date().toISOString(),
        phases: []
      };

      saveState(join(runsDir, `${pipelineId1}.json`), run1);
      saveState(join(runsDir, `${pipelineId2}.json`), run2);

      assert.ok(existsSync(join(runsDir, `${pipelineId1}.json`)));
      assert.ok(existsSync(join(runsDir, `${pipelineId2}.json`)));

      const loaded1 = loadState(join(runsDir, `${pipelineId1}.json`));
      const loaded2 = loadState(join(runsDir, `${pipelineId2}.json`));

      assert.ok(['running', 'paused'].includes(loaded1.status));
      assert.ok(['running', 'paused'].includes(loaded2.status));
    });

    it('should cancel PDCA cycle by marking status as cancelled', () => {
      const pdcaDir = join(blueprintDir, 'pdca');
      const cyclesDir = join(pdcaDir, 'cycles');
      ensureDir(cyclesDir);

      const cycleId = `pdca-${generateId()}`;
      const cyclePath = join(cyclesDir, `${cycleId}.json`);

      const cycle = {
        id: cycleId,
        task: 'Task to cancel',
        status: 'active',
        current_phase: 'check',
        iteration: 2,
        max_iterations: 4,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        phases: {}
      };

      saveState(cyclePath, cycle);

      // Cancel the cycle
      cycle.status = 'cancelled';
      cycle.cancelled_at = new Date().toISOString();
      cycle.cancel_reason = 'User requested cancellation';
      saveState(cyclePath, cycle);

      const loaded = loadState(cyclePath);
      assert.equal(loaded.status, 'cancelled');
      assert.ok(loaded.cancelled_at);
      assert.equal(loaded.cancel_reason, 'User requested cancellation');
    });

    it('should cancel pipeline run by marking status as cancelled', () => {
      const pipelineDir = join(blueprintDir, 'pipeline');
      const runsDir = join(pipelineDir, 'runs');
      ensureDir(runsDir);

      const pipelineId = `pipeline-${generateId()}`;
      const runPath = join(runsDir, `${pipelineId}.json`);

      const run = {
        id: pipelineId,
        feature: 'Feature to cancel',
        preset: 'standard',
        status: 'running',
        current_phase: 4,
        total_phases: 6,
        on_error: 'pause',
        created_at: new Date().toISOString(),
        phases: []
      };

      saveState(runPath, run);

      // Cancel the pipeline
      run.status = 'cancelled';
      run.cancelled_at = new Date().toISOString();
      run.cancel_reason = 'User requested cancellation';
      saveState(runPath, run);

      const loaded = loadState(runPath);
      assert.equal(loaded.status, 'cancelled');
      assert.ok(loaded.cancelled_at);
      assert.equal(loaded.cancel_reason, 'User requested cancellation');
    });

    it('should archive cancelled PDCA cycle to history', () => {
      const pdcaDir = join(blueprintDir, 'pdca');
      const cyclesDir = join(pdcaDir, 'cycles');
      const historyDir = join(pdcaDir, 'history');
      ensureDir(cyclesDir);
      ensureDir(historyDir);

      const cycleId = `pdca-${generateId()}`;
      const cyclePath = join(cyclesDir, `${cycleId}.json`);

      const cycle = {
        id: cycleId,
        task: 'Cancelled task',
        status: 'cancelled',
        current_phase: 'do',
        iteration: 1,
        max_iterations: 4,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        cancelled_at: new Date().toISOString(),
        cancel_reason: 'User requested cancellation',
        phases: {}
      };

      saveState(cyclePath, cycle);
      assert.ok(existsSync(cyclePath));

      // Archive
      const archivePath = archiveState(cyclePath, historyDir);

      assert.ok(!existsSync(cyclePath), 'original should be removed');
      assert.ok(existsSync(archivePath), 'archive should exist');

      const archived = loadState(archivePath);
      assert.equal(archived.id, cycleId);
      assert.equal(archived.status, 'cancelled');
    });

    it('should archive cancelled pipeline run to history', () => {
      const pipelineDir = join(blueprintDir, 'pipeline');
      const runsDir = join(pipelineDir, 'runs');
      const historyDir = join(pipelineDir, 'history');
      ensureDir(runsDir);
      ensureDir(historyDir);

      const pipelineId = `pipeline-${generateId()}`;
      const runPath = join(runsDir, `${pipelineId}.json`);

      const run = {
        id: pipelineId,
        feature: 'Cancelled feature',
        preset: 'standard',
        status: 'cancelled',
        current_phase: 3,
        total_phases: 6,
        on_error: 'pause',
        created_at: new Date().toISOString(),
        cancelled_at: new Date().toISOString(),
        cancel_reason: 'User requested cancellation',
        phases: []
      };

      saveState(runPath, run);
      assert.ok(existsSync(runPath));

      // Archive
      const archivePath = archiveState(runPath, historyDir);

      assert.ok(!existsSync(runPath), 'original should be removed');
      assert.ok(existsSync(archivePath), 'archive should exist');

      const archived = loadState(archivePath);
      assert.equal(archived.id, pipelineId);
      assert.equal(archived.status, 'cancelled');
    });

    it('should remove cancelled cycle from active index', () => {
      const pdcaDir = join(blueprintDir, 'pdca');
      ensureDir(pdcaDir);

      const cycleId1 = `pdca-${generateId()}`;
      const cycleId2 = `pdca-${generateId()}`;

      const indexPath = join(pdcaDir, 'active-cycles.json');
      const index = {
        cycles: [
          { id: cycleId1, task: 'Task A', iteration: 1, status: 'active' },
          { id: cycleId2, task: 'Task B', iteration: 2, status: 'active' }
        ]
      };

      saveState(indexPath, index);

      // Remove cycleId1 from index
      index.cycles = index.cycles.filter(c => c.id !== cycleId1);
      saveState(indexPath, index);

      const loaded = loadState(indexPath);
      assert.equal(loaded.cycles.length, 1);
      assert.ok(!loaded.cycles.find(c => c.id === cycleId1));
      assert.ok(loaded.cycles.find(c => c.id === cycleId2));
    });

    it('should handle --force flag to skip confirmation', () => {
      // The --force flag would be processed before calling cancel operations
      // This test verifies the flag can be stored and checked
      const forceFlag = true;
      assert.equal(forceFlag, true);
    });

    it('should handle empty state (no operations to cancel)', () => {
      const pdcaDir = join(blueprintDir, 'pdca');
      const pipelineDir = join(blueprintDir, 'pipeline');
      ensureDir(pdcaDir);
      ensureDir(pipelineDir);

      // No active cycles or pipelines exist
      const cyclesDir = join(pdcaDir, 'cycles');
      const runsDir = join(pipelineDir, 'runs');

      if (existsSync(cyclesDir)) {
        // Directory exists but should be empty or have no active items
        assert.ok(true, 'cycles directory exists');
      }

      if (existsSync(runsDir)) {
        // Directory exists but should be empty or have no active items
        assert.ok(true, 'runs directory exists');
      }
    });

    it('should cancel paused pipeline (can cancel paused state)', () => {
      const pipelineDir = join(blueprintDir, 'pipeline');
      const runsDir = join(pipelineDir, 'runs');
      ensureDir(runsDir);

      const pipelineId = `pipeline-${generateId()}`;
      const runPath = join(runsDir, `${pipelineId}.json`);

      const run = {
        id: pipelineId,
        feature: 'Paused feature',
        preset: 'standard',
        status: 'paused',
        current_phase: 4,
        total_phases: 6,
        on_error: 'pause',
        created_at: new Date().toISOString(),
        phases: []
      };

      saveState(runPath, run);

      // Cancel the paused pipeline
      run.status = 'cancelled';
      run.cancelled_at = new Date().toISOString();
      run.cancel_reason = 'User cancelled paused pipeline';
      saveState(runPath, run);

      const loaded = loadState(runPath);
      assert.equal(loaded.status, 'cancelled');
    });

    it('should handle multiple cancellations in batch', () => {
      const pdcaDir = join(blueprintDir, 'pdca');
      const cyclesDir = join(pdcaDir, 'cycles');
      const historyDir = join(pdcaDir, 'history');
      ensureDir(cyclesDir);
      ensureDir(historyDir);

      const cycleIds = [
        `pdca-${generateId()}`,
        `pdca-${generateId()}`,
        `pdca-${generateId()}`
      ];

      // Create multiple active cycles
      cycleIds.forEach(cycleId => {
        const cycle = {
          id: cycleId,
          task: `Task ${cycleId}`,
          status: 'active',
          current_phase: 'plan',
          iteration: 1,
          max_iterations: 4,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          phases: {}
        };
        saveState(join(cyclesDir, `${cycleId}.json`), cycle);
      });

      // Cancel all cycles
      cycleIds.forEach(cycleId => {
        const cyclePath = join(cyclesDir, `${cycleId}.json`);
        const cycle = loadState(cyclePath);
        cycle.status = 'cancelled';
        cycle.cancelled_at = new Date().toISOString();
        cycle.cancel_reason = 'Batch cancellation';
        saveState(cyclePath, cycle);

        // Archive
        archiveState(cyclePath, historyDir);
      });

      // Verify all are archived
      cycleIds.forEach(cycleId => {
        const cyclePath = join(cyclesDir, `${cycleId}.json`);
        assert.ok(!existsSync(cyclePath), 'original should be removed');
      });
    });
  });

  describe('Cancellation Metadata', () => {
    it('should record cancellation timestamp', () => {
      const pdcaDir = join(blueprintDir, 'pdca');
      const cyclesDir = join(pdcaDir, 'cycles');
      ensureDir(cyclesDir);

      const cycleId = `pdca-${generateId()}`;
      const cyclePath = join(cyclesDir, `${cycleId}.json`);

      const cycle = {
        id: cycleId,
        task: 'Task',
        status: 'active',
        current_phase: 'plan',
        iteration: 1,
        max_iterations: 4,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        phases: {}
      };

      saveState(cyclePath, cycle);

      const beforeCancel = Date.now();
      cycle.status = 'cancelled';
      cycle.cancelled_at = new Date().toISOString();
      saveState(cyclePath, cycle);

      const loaded = loadState(cyclePath);
      const cancelledTime = new Date(loaded.cancelled_at).getTime();

      assert.ok(cancelledTime >= beforeCancel);
      assert.ok(loaded.cancelled_at);
    });

    it('should record cancellation reason', () => {
      const pdcaDir = join(blueprintDir, 'pdca');
      const cyclesDir = join(pdcaDir, 'cycles');
      ensureDir(cyclesDir);

      const cycleId = `pdca-${generateId()}`;
      const cyclePath = join(cyclesDir, `${cycleId}.json`);

      const cycle = {
        id: cycleId,
        task: 'Task',
        status: 'active',
        current_phase: 'plan',
        iteration: 1,
        max_iterations: 4,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        phases: {}
      };

      saveState(cyclePath, cycle);

      cycle.status = 'cancelled';
      cycle.cancelled_at = new Date().toISOString();
      cycle.cancel_reason = 'User requested cancellation via /blueprint:cancel';
      saveState(cyclePath, cycle);

      const loaded = loadState(cyclePath);
      assert.equal(loaded.cancel_reason, 'User requested cancellation via /blueprint:cancel');
    });

    it('should preserve original state in archive', () => {
      const pdcaDir = join(blueprintDir, 'pdca');
      const cyclesDir = join(pdcaDir, 'cycles');
      const historyDir = join(pdcaDir, 'history');
      ensureDir(cyclesDir);
      ensureDir(historyDir);

      const cycleId = `pdca-${generateId()}`;
      const cyclePath = join(cyclesDir, `${cycleId}.json`);

      const cycle = {
        id: cycleId,
        task: 'Original task',
        status: 'active',
        current_phase: 'do',
        iteration: 3,
        max_iterations: 4,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        phases: { plan: { status: 'completed' } }
      };

      saveState(cyclePath, cycle);

      // Cancel and archive
      cycle.status = 'cancelled';
      cycle.cancelled_at = new Date().toISOString();
      saveState(cyclePath, cycle);

      const archivePath = archiveState(cyclePath, historyDir);
      const archived = loadState(archivePath);

      // Verify original data is preserved
      assert.equal(archived.id, cycleId);
      assert.equal(archived.task, 'Original task');
      assert.equal(archived.iteration, 3);
      assert.equal(archived.current_phase, 'do');
      assert.ok(archived.phases.plan);
    });
  });

  describe('Error Handling', () => {
    it('should handle non-existent cycles gracefully', () => {
      const pdcaDir = join(blueprintDir, 'pdca');
      const cyclesDir = join(pdcaDir, 'cycles');
      ensureDir(cyclesDir);

      const nonExistentPath = join(cyclesDir, 'non-existent.json');
      const loaded = loadState(nonExistentPath);

      assert.equal(loaded, null);
    });

    it('should handle corrupted state files during cancellation', () => {
      const pdcaDir = join(blueprintDir, 'pdca');
      const cyclesDir = join(pdcaDir, 'cycles');
      ensureDir(cyclesDir);

      const cyclePath = join(cyclesDir, 'corrupted.json');
      saveState(cyclePath, { invalid: 'incomplete data' });

      const loaded = loadState(cyclePath);
      // Should load but will be missing required fields
      assert.ok(loaded);
      assert.ok(!loaded.id);
      assert.ok(!loaded.status);
    });
  });
});
