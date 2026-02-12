import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  PDCA_PHASES,
  PIPELINE_PHASES,
  PIPELINE_PRESETS,
  STATE_PATHS,
  GAP_SEVERITY,
  CYCLE_STATUS,
  RUN_STATUS,
  ON_ERROR
} from '../../hooks/lib/constants.mjs';

describe('constants.mjs', () => {

  describe('PDCA_PHASES', () => {
    it('should have exactly 4 elements', () => {
      assert.equal(PDCA_PHASES.length, 4);
    });

    it('should contain Plan, Do, Check, Act in lowercase', () => {
      assert.deepStrictEqual(PDCA_PHASES, ['plan', 'do', 'check', 'act']);
    });

    it('should be an array', () => {
      assert.ok(Array.isArray(PDCA_PHASES));
    });
  });

  describe('PIPELINE_PHASES', () => {
    it('should exist and be an array', () => {
      assert.ok(Array.isArray(PIPELINE_PHASES));
    });

    it('should have 9 phases for the full preset', () => {
      assert.equal(PIPELINE_PHASES.length, 9);
    });

    it('should contain expected phase names', () => {
      const expected = [
        'requirements', 'architecture', 'design', 'implementation',
        'unit-test', 'integration-test', 'code-review', 'gap-analysis', 'verification'
      ];
      assert.deepStrictEqual(PIPELINE_PHASES, expected);
    });
  });

  describe('PIPELINE_PRESETS', () => {
    it('should have full, standard, and minimal presets', () => {
      assert.ok('full' in PIPELINE_PRESETS);
      assert.ok('standard' in PIPELINE_PRESETS);
      assert.ok('minimal' in PIPELINE_PRESETS);
    });

    it('full preset should reference all 9 phase indices', () => {
      assert.deepStrictEqual(PIPELINE_PRESETS.full.phases, [0, 1, 2, 3, 4, 5, 6, 7, 8]);
    });

    it('minimal preset should reference 3 phase indices', () => {
      assert.equal(PIPELINE_PRESETS.minimal.phases.length, 3);
    });

    it('each preset should have a description string', () => {
      for (const [, preset] of Object.entries(PIPELINE_PRESETS)) {
        assert.equal(typeof preset.description, 'string');
        assert.ok(preset.description.length > 0);
      }
    });
  });

  describe('STATE_PATHS', () => {
    it('should have pdca, gaps, and pipeline keys', () => {
      assert.ok('pdca' in STATE_PATHS);
      assert.ok('gaps' in STATE_PATHS);
      assert.ok('pipeline' in STATE_PATHS);
    });

    it('pdca should have cycles, activeCycles, and history paths', () => {
      assert.equal(typeof STATE_PATHS.pdca.cycles, 'string');
      assert.equal(typeof STATE_PATHS.pdca.activeCycles, 'string');
      assert.equal(typeof STATE_PATHS.pdca.history, 'string');
    });

    it('gaps should have analyses and reports paths', () => {
      assert.equal(typeof STATE_PATHS.gaps.analyses, 'string');
      assert.equal(typeof STATE_PATHS.gaps.reports, 'string');
    });

    it('pipeline should have runs and phases paths', () => {
      assert.equal(typeof STATE_PATHS.pipeline.runs, 'string');
      assert.equal(typeof STATE_PATHS.pipeline.phases, 'string');
    });
  });

  describe('GAP_SEVERITY', () => {
    it('should have CRITICAL, HIGH, MEDIUM, LOW keys', () => {
      assert.ok('CRITICAL' in GAP_SEVERITY);
      assert.ok('HIGH' in GAP_SEVERITY);
      assert.ok('MEDIUM' in GAP_SEVERITY);
      assert.ok('LOW' in GAP_SEVERITY);
    });

    it('severity levels should increase from LOW to CRITICAL', () => {
      assert.ok(GAP_SEVERITY.CRITICAL.level > GAP_SEVERITY.HIGH.level);
      assert.ok(GAP_SEVERITY.HIGH.level > GAP_SEVERITY.MEDIUM.level);
      assert.ok(GAP_SEVERITY.MEDIUM.level > GAP_SEVERITY.LOW.level);
    });
  });

  describe('CYCLE_STATUS', () => {
    it('should have ACTIVE, SUSPENDED, COMPLETED, CANCELLED statuses', () => {
      assert.equal(CYCLE_STATUS.ACTIVE, 'active');
      assert.equal(CYCLE_STATUS.SUSPENDED, 'suspended');
      assert.equal(CYCLE_STATUS.COMPLETED, 'completed');
      assert.equal(CYCLE_STATUS.CANCELLED, 'cancelled');
    });
  });

  describe('RUN_STATUS', () => {
    it('should have RUNNING, PAUSED, COMPLETED, CANCELLED, FAILED statuses', () => {
      assert.equal(RUN_STATUS.RUNNING, 'running');
      assert.equal(RUN_STATUS.PAUSED, 'paused');
      assert.equal(RUN_STATUS.COMPLETED, 'completed');
      assert.equal(RUN_STATUS.CANCELLED, 'cancelled');
      assert.equal(RUN_STATUS.FAILED, 'failed');
    });
  });

  describe('ON_ERROR', () => {
    it('should have ABORT, SKIP, PAUSE modes', () => {
      assert.equal(ON_ERROR.ABORT, 'abort');
      assert.equal(ON_ERROR.SKIP, 'skip');
      assert.equal(ON_ERROR.PAUSE, 'pause');
    });
  });
});
