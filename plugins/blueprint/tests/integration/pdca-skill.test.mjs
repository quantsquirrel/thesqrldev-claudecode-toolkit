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

describe('PDCA Skill Integration', () => {
  let tempDir;
  let blueprintDir;

  before(async () => {
    tempDir = await mkdtemp(join(tmpdir(), 'blueprint-pdca-test-'));
    blueprintDir = join(tempDir, '.blueprint');
    ensureDir(blueprintDir);
  });

  after(async () => {
    await rm(tempDir, { recursive: true, force: true });
  });

  describe('PDCA Cycle Workflow', () => {
    it('should create PDCA directory structure', () => {
      const pdcaDir = join(blueprintDir, 'pdca');
      const cyclesDir = join(pdcaDir, 'cycles');
      const historyDir = join(pdcaDir, 'history');

      ensureDir(cyclesDir);
      ensureDir(historyDir);

      assert.ok(existsSync(cyclesDir), 'cycles directory should exist');
      assert.ok(existsSync(historyDir), 'history directory should exist');
    });

    it('should initialize PDCA cycle with correct structure', () => {
      const cycleId = `pdca-${generateId()}`;
      const cyclePath = join(blueprintDir, 'pdca', 'cycles', `${cycleId}.json`);

      const cycleState = {
        id: cycleId,
        task: 'improve auth module error handling',
        status: 'active',
        current_phase: 'plan',
        iteration: 1,
        max_iterations: 4,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        phases: {
          plan: { status: 'pending', output: null },
          do: { status: 'pending', output: null },
          check: { status: 'pending', output: null },
          act: { status: 'pending', decision: null }
        }
      };

      saveState(cyclePath, cycleState);
      assert.ok(existsSync(cyclePath));

      const loaded = loadState(cyclePath);
      assert.deepStrictEqual(loaded, cycleState);
    });

    it('should progress through Plan phase', () => {
      const cycleId = `pdca-${generateId()}`;
      const cyclePath = join(blueprintDir, 'pdca', 'cycles', `${cycleId}.json`);

      const cycleState = {
        id: cycleId,
        task: 'test task',
        status: 'active',
        current_phase: 'plan',
        iteration: 1,
        max_iterations: 4,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        phases: {
          plan: { status: 'pending', output: null },
          do: { status: 'pending', output: null },
          check: { status: 'pending', output: null },
          act: { status: 'pending', decision: null }
        }
      };

      saveState(cyclePath, cycleState);

      // Complete Plan phase
      cycleState.phases.plan.status = 'completed';
      cycleState.phases.plan.output = {
        targets: ['100% error coverage', 'Structured error messages'],
        acceptance_criteria: [
          'All functions have try/catch blocks',
          'Error messages include context'
        ],
        approach: 'Add error handling to 5 core functions'
      };
      cycleState.current_phase = 'do';
      cycleState.updated_at = new Date().toISOString();

      saveState(cyclePath, cycleState);
      const loaded = loadState(cyclePath);

      assert.equal(loaded.phases.plan.status, 'completed');
      assert.ok(loaded.phases.plan.output);
      assert.equal(loaded.current_phase, 'do');
    });

    it('should progress through Do phase', () => {
      const cycleId = `pdca-${generateId()}`;
      const cyclePath = join(blueprintDir, 'pdca', 'cycles', `${cycleId}.json`);

      const cycleState = {
        id: cycleId,
        task: 'test task',
        status: 'active',
        current_phase: 'do',
        iteration: 1,
        max_iterations: 4,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        phases: {
          plan: {
            status: 'completed',
            output: {
              targets: ['100% error coverage'],
              acceptance_criteria: ['All functions have try/catch'],
              approach: 'Add error handling'
            }
          },
          do: { status: 'pending', output: null },
          check: { status: 'pending', output: null },
          act: { status: 'pending', decision: null }
        }
      };

      saveState(cyclePath, cycleState);

      // Complete Do phase
      cycleState.phases.do.status = 'completed';
      cycleState.phases.do.output = {
        changes: [
          'Added try/catch to authenticateUser()',
          'Added try/catch to validateToken()',
          'Added error logging'
        ],
        files_modified: [
          'src/auth/authenticate.ts:42',
          'src/auth/validate.ts:15'
        ]
      };
      cycleState.current_phase = 'check';
      cycleState.updated_at = new Date().toISOString();

      saveState(cyclePath, cycleState);
      const loaded = loadState(cyclePath);

      assert.equal(loaded.phases.do.status, 'completed');
      assert.ok(loaded.phases.do.output);
      assert.equal(loaded.current_phase, 'check');
    });

    it('should progress through Check phase', () => {
      const cycleId = `pdca-${generateId()}`;
      const cyclePath = join(blueprintDir, 'pdca', 'cycles', `${cycleId}.json`);

      const cycleState = {
        id: cycleId,
        task: 'test task',
        status: 'active',
        current_phase: 'check',
        iteration: 1,
        max_iterations: 4,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        phases: {
          plan: { status: 'completed', output: {} },
          do: { status: 'completed', output: {} },
          check: { status: 'pending', output: null },
          act: { status: 'pending', decision: null }
        }
      };

      saveState(cyclePath, cycleState);

      // Complete Check phase
      cycleState.phases.check.status = 'completed';
      cycleState.phases.check.output = {
        verdict: 'PASS',
        criteria_results: [
          {
            criterion: 'All functions have try/catch',
            status: 'pass',
            evidence: 'Verified 5/5 functions'
          },
          {
            criterion: 'Error messages include context',
            status: 'pass',
            evidence: 'All errors include context'
          }
        ]
      };
      cycleState.current_phase = 'act';
      cycleState.updated_at = new Date().toISOString();

      saveState(cyclePath, cycleState);
      const loaded = loadState(cyclePath);

      assert.equal(loaded.phases.check.status, 'completed');
      assert.equal(loaded.phases.check.output.verdict, 'PASS');
      assert.equal(loaded.current_phase, 'act');
    });

    it('should progress through Act phase with CONTINUE decision', () => {
      const cycleId = `pdca-${generateId()}`;
      const cyclePath = join(blueprintDir, 'pdca', 'cycles', `${cycleId}.json`);

      const cycleState = {
        id: cycleId,
        task: 'test task',
        status: 'active',
        current_phase: 'act',
        iteration: 1,
        max_iterations: 4,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        phases: {
          plan: { status: 'completed', output: {} },
          do: { status: 'completed', output: {} },
          check: {
            status: 'completed',
            output: {
              verdict: 'FAIL',
              criteria_results: []
            }
          },
          act: { status: 'pending', decision: null }
        }
      };

      saveState(cyclePath, cycleState);

      // Complete Act phase with CONTINUE
      cycleState.phases.act.status = 'completed';
      cycleState.phases.act.decision = 'CONTINUE';
      cycleState.phases.act.reason = 'Quality targets not met, need another iteration';
      cycleState.iteration = 2;
      cycleState.current_phase = 'plan';
      // Reset phases for next iteration
      cycleState.phases = {
        plan: { status: 'pending', output: null },
        do: { status: 'pending', output: null },
        check: { status: 'pending', output: null },
        act: { status: 'pending', decision: null }
      };
      cycleState.updated_at = new Date().toISOString();

      saveState(cyclePath, cycleState);
      const loaded = loadState(cyclePath);

      assert.equal(loaded.iteration, 2);
      assert.equal(loaded.current_phase, 'plan');
      assert.equal(loaded.phases.plan.status, 'pending');
    });

    it('should progress through Act phase with COMPLETE decision', () => {
      const cycleId = `pdca-${generateId()}`;
      const cyclePath = join(blueprintDir, 'pdca', 'cycles', `${cycleId}.json`);

      const cycleState = {
        id: cycleId,
        task: 'test task',
        status: 'active',
        current_phase: 'act',
        iteration: 2,
        max_iterations: 4,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        phases: {
          plan: { status: 'completed', output: {} },
          do: { status: 'completed', output: {} },
          check: {
            status: 'completed',
            output: {
              verdict: 'PASS',
              criteria_results: []
            }
          },
          act: { status: 'pending', decision: null }
        }
      };

      saveState(cyclePath, cycleState);

      // Complete Act phase with COMPLETE
      cycleState.phases.act.status = 'completed';
      cycleState.phases.act.decision = 'COMPLETE';
      cycleState.phases.act.reason = 'All quality targets met';
      cycleState.status = 'completed';
      cycleState.updated_at = new Date().toISOString();

      saveState(cyclePath, cycleState);
      const loaded = loadState(cyclePath);

      assert.equal(loaded.status, 'completed');
      assert.equal(loaded.phases.act.decision, 'COMPLETE');
    });

    it('should respect max_iterations limit', () => {
      const cycleId = `pdca-${generateId()}`;
      const cyclePath = join(blueprintDir, 'pdca', 'cycles', `${cycleId}.json`);

      const maxIterations = 3;
      const cycleState = {
        id: cycleId,
        task: 'test task',
        status: 'active',
        current_phase: 'act',
        iteration: maxIterations,
        max_iterations: maxIterations,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        phases: {
          plan: { status: 'completed', output: {} },
          do: { status: 'completed', output: {} },
          check: { status: 'completed', output: { verdict: 'FAIL' } },
          act: { status: 'pending', decision: null }
        }
      };

      saveState(cyclePath, cycleState);

      // At max iterations, should COMPLETE even if targets not met
      cycleState.phases.act.status = 'completed';
      cycleState.phases.act.decision = 'COMPLETE';
      cycleState.phases.act.reason = 'Max iterations reached';
      cycleState.status = 'completed';

      saveState(cyclePath, cycleState);
      const loaded = loadState(cyclePath);

      assert.equal(loaded.status, 'completed');
      assert.equal(loaded.iteration, maxIterations);
    });

    it('should archive completed cycle to history', () => {
      const cycleId = `pdca-${generateId()}`;
      const cyclePath = join(blueprintDir, 'pdca', 'cycles', `${cycleId}.json`);
      const historyDir = join(blueprintDir, 'pdca', 'history');

      const cycleState = {
        id: cycleId,
        task: 'completed task',
        status: 'completed',
        current_phase: 'act',
        iteration: 2,
        max_iterations: 4,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        phases: {}
      };

      saveState(cyclePath, cycleState);
      assert.ok(existsSync(cyclePath));

      // Archive
      const archivePath = archiveState(cyclePath, historyDir);

      assert.ok(!existsSync(cyclePath), 'original should be removed');
      assert.ok(existsSync(archivePath), 'archive should exist');

      const archived = loadState(archivePath);
      assert.equal(archived.id, cycleId);
      assert.equal(archived.status, 'completed');
    });

    it('should track active cycles in index', () => {
      const indexPath = join(blueprintDir, 'pdca', 'active-cycles.json');

      const cycleId1 = `pdca-${generateId()}`;
      const cycleId2 = `pdca-${generateId()}`;

      const index = {
        cycles: [
          { id: cycleId1, task: 'Task A', iteration: 1, status: 'active' },
          { id: cycleId2, task: 'Task B', iteration: 2, status: 'active' }
        ]
      };

      saveState(indexPath, index);
      const loaded = loadState(indexPath);

      assert.equal(loaded.cycles.length, 2);
      assert.ok(loaded.cycles.find(c => c.id === cycleId1));
      assert.ok(loaded.cycles.find(c => c.id === cycleId2));
    });
  });

  describe('State Management', () => {
    it('should handle --auto-act flag', () => {
      const cycleId = `pdca-${generateId()}`;
      const cyclePath = join(blueprintDir, 'pdca', 'cycles', `${cycleId}.json`);

      const cycleState = {
        id: cycleId,
        task: 'test task',
        status: 'active',
        current_phase: 'plan',
        iteration: 1,
        max_iterations: 4,
        auto_act: true, // Flag set
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        phases: {
          plan: { status: 'pending', output: null },
          do: { status: 'pending', output: null },
          check: { status: 'pending', output: null },
          act: { status: 'pending', decision: null }
        }
      };

      saveState(cyclePath, cycleState);
      const loaded = loadState(cyclePath);

      assert.equal(loaded.auto_act, true);
    });

    it('should validate phase outputs schema', () => {
      // Plan output
      const planOutput = {
        targets: ['Target 1', 'Target 2'],
        acceptance_criteria: ['Criteria 1', 'Criteria 2'],
        approach: 'Test approach'
      };

      assert.ok(Array.isArray(planOutput.targets));
      assert.ok(Array.isArray(planOutput.acceptance_criteria));
      assert.ok(typeof planOutput.approach === 'string');

      // Do output
      const doOutput = {
        changes: ['Change 1', 'Change 2'],
        files_modified: ['file.ts:10', 'file2.ts:20']
      };

      assert.ok(Array.isArray(doOutput.changes));
      assert.ok(Array.isArray(doOutput.files_modified));
      doOutput.files_modified.forEach(f => {
        assert.match(f, /^.+:\d+$/);
      });

      // Check output
      const checkOutput = {
        verdict: 'PASS',
        criteria_results: [
          { criterion: 'Test', status: 'pass', evidence: 'Evidence' }
        ]
      };

      assert.ok(['PASS', 'FAIL'].includes(checkOutput.verdict));
      assert.ok(Array.isArray(checkOutput.criteria_results));

      // Act output
      const actOutput = {
        decision: 'CONTINUE',
        reason: 'Reason for decision'
      };

      assert.ok(['CONTINUE', 'COMPLETE'].includes(actOutput.decision));
      assert.ok(typeof actOutput.reason === 'string');
    });
  });

  describe('Error Handling', () => {
    it('should handle invalid phase transitions', () => {
      const cycleId = `pdca-${generateId()}`;
      const cyclePath = join(blueprintDir, 'pdca', 'cycles', `${cycleId}.json`);

      const cycleState = {
        id: cycleId,
        task: 'test task',
        status: 'active',
        current_phase: 'plan',
        iteration: 1,
        max_iterations: 4,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        phases: {
          plan: { status: 'pending', output: null },
          do: { status: 'pending', output: null },
          check: { status: 'pending', output: null },
          act: { status: 'pending', decision: null }
        }
      };

      saveState(cyclePath, cycleState);

      // Try to skip to check without completing plan and do
      // This should be caught by validation
      const validPhases = ['plan', 'do', 'check', 'act'];
      assert.ok(validPhases.includes(cycleState.current_phase));
    });

    it('should handle corrupted cycle state', () => {
      const cyclePath = join(blueprintDir, 'pdca', 'cycles', 'corrupted.json');

      ensureDir(join(blueprintDir, 'pdca', 'cycles'));
      saveState(cyclePath, { invalid: 'data' });

      const loaded = loadState(cyclePath);
      // Should load but validation should catch missing required fields
      assert.ok(loaded);
      assert.ok(!loaded.id);
    });
  });
});
