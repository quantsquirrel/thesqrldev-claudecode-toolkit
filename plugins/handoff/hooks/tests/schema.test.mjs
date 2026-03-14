/**
 * Schema Module Tests
 *
 * Covers:
 *   - schema.mjs: SCHEMA_VERSION, HANDOFF_SCHEMA, validateHandoff, createEmptyHandoff
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  SCHEMA_VERSION,
  HANDOFF_SCHEMA,
  validateHandoff,
  createEmptyHandoff,
} from '../schema.mjs';

// ---------------------------------------------------------------------------
// SCHEMA_VERSION
// ---------------------------------------------------------------------------

describe('SCHEMA_VERSION', () => {
  it('is a non-empty string', () => {
    assert.equal(typeof SCHEMA_VERSION, 'string');
    assert.ok(SCHEMA_VERSION.length > 0);
  });

  it('follows semver-like pattern starting with v', () => {
    assert.match(SCHEMA_VERSION, /^v\d+/);
  });
});

// ---------------------------------------------------------------------------
// HANDOFF_SCHEMA
// ---------------------------------------------------------------------------

describe('HANDOFF_SCHEMA', () => {
  it('contains schema_version matching SCHEMA_VERSION constant', () => {
    assert.equal(HANDOFF_SCHEMA.schema_version, SCHEMA_VERSION);
  });

  it('has summary.natural_language as a string', () => {
    assert.equal(typeof HANDOFF_SCHEMA.summary.natural_language, 'string');
  });

  it('has summary.structured_data with required array fields', () => {
    const sd = HANDOFF_SCHEMA.summary.structured_data;

    assert.ok(Array.isArray(sd.files_modified));
    assert.ok(Array.isArray(sd.functions_touched));
    assert.ok(Array.isArray(sd.failed_approaches));
    assert.ok(Array.isArray(sd.decisions));
  });
});

// ---------------------------------------------------------------------------
// validateHandoff
// ---------------------------------------------------------------------------

describe('validateHandoff', () => {
  it('returns true for a valid handoff object', () => {
    const handoff = {
      summary: {
        natural_language: 'Session summary here',
        structured_data: {
          files_modified: [{ path: 'src/a.ts', lines: [1], type: 'edit' }],
          functions_touched: [],
          failed_approaches: [],
          decisions: [],
        },
      },
    };

    assert.equal(validateHandoff(handoff), true);
  });

  it('returns true for a minimal valid handoff with empty arrays', () => {
    const handoff = createEmptyHandoff();
    assert.equal(validateHandoff(handoff), true);
  });

  it('returns false when handoff is null', () => {
    assert.equal(validateHandoff(null), false);
  });

  it('returns false when handoff is undefined', () => {
    assert.equal(validateHandoff(undefined), false);
  });

  it('returns false when summary is missing', () => {
    assert.equal(validateHandoff({}), false);
  });

  it('returns false when natural_language is not a string', () => {
    const handoff = {
      summary: {
        natural_language: 123,
        structured_data: {
          files_modified: [],
          functions_touched: [],
          failed_approaches: [],
          decisions: [],
        },
      },
    };

    assert.equal(validateHandoff(handoff), false);
  });

  it('returns false when structured_data is missing', () => {
    const handoff = {
      summary: {
        natural_language: 'Summary',
      },
    };

    assert.equal(validateHandoff(handoff), false);
  });

  it('returns false when files_modified is not an array', () => {
    const handoff = {
      summary: {
        natural_language: 'Summary',
        structured_data: {
          files_modified: 'not-an-array',
          functions_touched: [],
          failed_approaches: [],
          decisions: [],
        },
      },
    };

    assert.equal(validateHandoff(handoff), false);
  });

  it('returns false when functions_touched is missing', () => {
    const handoff = {
      summary: {
        natural_language: 'Summary',
        structured_data: {
          files_modified: [],
          failed_approaches: [],
          decisions: [],
        },
      },
    };

    assert.equal(validateHandoff(handoff), false);
  });

  it('returns false when failed_approaches is not an array', () => {
    const handoff = {
      summary: {
        natural_language: 'Summary',
        structured_data: {
          files_modified: [],
          functions_touched: [],
          failed_approaches: null,
          decisions: [],
        },
      },
    };

    assert.equal(validateHandoff(handoff), false);
  });

  it('returns false when decisions is not an array', () => {
    const handoff = {
      summary: {
        natural_language: 'Summary',
        structured_data: {
          files_modified: [],
          functions_touched: [],
          failed_approaches: [],
          decisions: 'not-array',
        },
      },
    };

    assert.equal(validateHandoff(handoff), false);
  });
});

// ---------------------------------------------------------------------------
// createEmptyHandoff
// ---------------------------------------------------------------------------

describe('createEmptyHandoff', () => {
  it('returns an object with empty natural_language', () => {
    const handoff = createEmptyHandoff();
    assert.equal(handoff.summary.natural_language, '');
  });

  it('returns an object with empty structured_data arrays', () => {
    const handoff = createEmptyHandoff();
    const sd = handoff.summary.structured_data;

    assert.deepEqual(sd.files_modified, []);
    assert.deepEqual(sd.functions_touched, []);
    assert.deepEqual(sd.failed_approaches, []);
    assert.deepEqual(sd.decisions, []);
  });

  it('returns a new object each time (no shared references)', () => {
    const a = createEmptyHandoff();
    const b = createEmptyHandoff();

    a.summary.structured_data.files_modified.push({ path: 'x.ts' });

    assert.equal(b.summary.structured_data.files_modified.length, 0);
  });

  it('passes validation', () => {
    const handoff = createEmptyHandoff();
    assert.equal(validateHandoff(handoff), true);
  });
});
