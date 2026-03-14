/**
 * Security Module Tests
 *
 * Covers: maskSensitiveData (JWT, Bearer, AWS keys, API keys, env vars, base64),
 *         validateKeyName (allowed vs forbidden key names)
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  SECURITY_PATTERNS,
  SAFE_KEY_SCHEMA,
  maskSensitiveData,
  validateKeyName,
} from '../constants.mjs';

const REDACTED = '***REDACTED***';

// ---------------------------------------------------------------------------
// maskSensitiveData
// ---------------------------------------------------------------------------

describe('maskSensitiveData', () => {

  it('returns plain text unchanged when no sensitive data present', () => {
    const input = 'This is a normal log message with no secrets.';
    assert.equal(maskSensitiveData(input), input);
  });

  // -- JWT tokens --

  it('masks a JWT token', () => {
    const jwt =
      'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
      'eyJzdWIiOiIxMjM0NTY3ODkwIn0.' +
      'dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U';
    const input = `Authorization: ${jwt}`;
    const result = maskSensitiveData(input);
    assert.ok(!result.includes('eyJ'), 'JWT header should be masked');
  });

  // -- Bearer tokens --

  it('masks a Bearer token', () => {
    const input = 'Bearer sk-ant-api03-abc123xyz';
    const result = maskSensitiveData(input);
    assert.ok(!result.includes('sk-ant-api03'), 'Bearer value should be masked');
    assert.ok(result.includes(REDACTED));
  });

  it('masks Bearer token case-insensitively', () => {
    const input = 'bearer my-secret-token-value';
    const result = maskSensitiveData(input);
    assert.ok(!result.includes('my-secret-token-value'));
  });

  // -- AWS Access Keys --

  it('masks an AWS access key', () => {
    const input = 'aws_access_key_id = AKIAIOSFODNN7EXAMPLE';
    const result = maskSensitiveData(input);
    assert.ok(!result.includes('AKIAIOSFODNN7EXAMPLE'), 'AWS key should be masked');
  });

  // -- Generic API keys / secrets --

  it('masks api_key=value patterns', () => {
    const input = 'api_key=sk_live_abc123def456';
    const result = maskSensitiveData(input);
    assert.ok(!result.includes('sk_live_abc123def456'));
  });

  it('masks API-KEY: value patterns', () => {
    const input = 'API-KEY: "my-super-secret"';
    const result = maskSensitiveData(input);
    assert.ok(!result.includes('my-super-secret'));
  });

  it('masks secret=value patterns', () => {
    const input = 'client_secret=whsec_abcdef123456';
    const result = maskSensitiveData(input);
    assert.ok(!result.includes('whsec_abcdef123456'));
  });

  it('masks token=value patterns', () => {
    const input = 'access_token="ghp_xxxxxxxxxxxxxxxxxxxx"';
    const result = maskSensitiveData(input);
    assert.ok(!result.includes('ghp_xxxxxxxxxxxxxxxxxxxx'));
  });

  it('masks password=value patterns', () => {
    const input = 'db_password=P@ssw0rd!2024';
    const result = maskSensitiveData(input);
    assert.ok(!result.includes('P@ssw0rd!2024'));
  });

  // -- Environment variable references --

  it('masks process.env references', () => {
    const input = 'const key = process.env.OPENAI_API_KEY;';
    const result = maskSensitiveData(input);
    assert.ok(!result.includes('process.env.OPENAI_API_KEY'));
  });

  // -- Base64 encoded secrets --

  it('masks long base64-encoded strings (40+ chars)', () => {
    const b64 = 'YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY3ODkw'; // 48 chars
    const input = `secret: ${b64}`;
    const result = maskSensitiveData(input);
    assert.ok(!result.includes(b64), 'Long base64 string should be masked');
  });

  it('does not mask short base64-like strings (under 40 chars)', () => {
    const shortB64 = 'YWJjZGVm'; // 8 chars, valid base64 but short
    const input = `value: ${shortB64}`;
    const result = maskSensitiveData(input);
    assert.ok(result.includes(shortB64), 'Short base64 should NOT be masked');
  });

  // -- GCP service account key --

  it('masks a GCP service account JSON key', () => {
    const input = '{"type": "service_account", "project_id": "my-project"}';
    const result = maskSensitiveData(input);
    assert.ok(!result.includes('"service_account"'), 'GCP service account type should be masked');
  });

  // -- PEM private key --

  it('masks a PEM private key header', () => {
    const input = '-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBg...';
    const result = maskSensitiveData(input);
    assert.ok(!result.includes('-----BEGIN PRIVATE KEY-----'), 'PEM header should be masked');
  });

  it('masks an RSA PEM private key header', () => {
    const input = '-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQ...';
    const result = maskSensitiveData(input);
    assert.ok(!result.includes('-----BEGIN RSA PRIVATE KEY-----'), 'RSA PEM header should be masked');
  });

  // -- Stripe secret key --

  it('masks a Stripe secret key', () => {
    const prefix = 'sk_live_';
    const suffix = 'FAKE00TEST00KEY00ONLY0000';
    const input = 'key: ' + prefix + suffix;
    const result = maskSensitiveData(input);
    assert.ok(!result.includes(prefix + suffix), 'Stripe sk_live_ key should be masked');
  });

  // -- GitHub fine-grained PAT --

  it('masks a GitHub fine-grained PAT', () => {
    const input = 'token=github_pat_11ABCDEF0_abcdefghijklmnopqrstuvwxyz';
    const result = maskSensitiveData(input);
    assert.ok(!result.includes('github_pat_11ABCDEF0_abcdefghijklmnopqrstuvwxyz'), 'GitHub PAT should be masked');
  });

  // -- Multiple sensitive values in one string --

  it('masks multiple sensitive values in a single string', () => {
    const input = [
      'Bearer secret-token-123',
      'api_key=sk_live_xyz',
      'process.env.DATABASE_URL',
    ].join('\n');
    const result = maskSensitiveData(input);
    assert.ok(!result.includes('secret-token-123'));
    assert.ok(!result.includes('sk_live_xyz'));
    assert.ok(!result.includes('process.env.DATABASE_URL'));
  });
});

// ---------------------------------------------------------------------------
// validateKeyName
// ---------------------------------------------------------------------------

describe('validateKeyName', () => {

  it('accepts allowed key names', () => {
    for (const key of SAFE_KEY_SCHEMA.ALLOWED_KEYS) {
      assert.equal(validateKeyName(key), true, `"${key}" should be valid`);
    }
  });

  it('rejects key names containing "password"', () => {
    assert.equal(validateKeyName('user_password'), false);
    assert.equal(validateKeyName('PASSWORD_HASH'), false);
  });

  it('rejects key names containing "secret"', () => {
    assert.equal(validateKeyName('client_secret'), false);
  });

  it('rejects key names containing "token"', () => {
    assert.equal(validateKeyName('access_token'), false);
  });

  it('rejects key names containing "key"', () => {
    assert.equal(validateKeyName('api_key'), false);
  });

  it('rejects key names containing "credential"', () => {
    assert.equal(validateKeyName('user_credential'), false);
  });

  it('rejects key names containing "ssn"', () => {
    assert.equal(validateKeyName('customer_ssn'), false);
  });

  it('rejects key names containing "email"', () => {
    assert.equal(validateKeyName('user_email'), false);
  });

  it('accepts arbitrary safe key names', () => {
    assert.equal(validateKeyName('summary'), true);
    assert.equal(validateKeyName('task_description'), true);
    assert.equal(validateKeyName('progress'), true);
  });
});
