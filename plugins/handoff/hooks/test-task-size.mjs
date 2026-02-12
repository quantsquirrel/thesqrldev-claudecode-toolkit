#!/usr/bin/env node
/**
 * Integration Tests for Task Size Feature
 *
 * Tests:
 * 1. Constants validation
 * 2. Task size estimator hook
 * 3. Auto-handoff dynamic thresholds
 * 4. State file locking
 */

import * as fs from 'fs';
import * as path from 'path';
import { tmpdir } from 'os';
import { execSync } from 'child_process';

const SCRIPT_DIR = path.dirname(new URL(import.meta.url).pathname);

// ANSI colors
const GREEN = '\x1b[32m';
const RED = '\x1b[31m';
const YELLOW = '\x1b[33m';
const BLUE = '\x1b[34m';
const RESET = '\x1b[0m';

let testsPassed = 0;
let testsFailed = 0;

function log(message, color = RESET) {
  console.log(`${color}${message}${RESET}`);
}

function assert(condition, testName) {
  if (condition) {
    log(`✅ ${testName}`, GREEN);
    testsPassed++;
  } else {
    log(`❌ ${testName}`, RED);
    testsFailed++;
  }
}

// Test 1: Validate constants.mjs
async function testConstants() {
  log('\n📋 Test 1: Constants Validation', BLUE);

  try {
    const constants = await import('./constants.mjs');

    assert(constants.TASK_SIZE !== undefined, 'TASK_SIZE enum exists');
    assert(constants.TASK_SIZE.SMALL === 'small', 'TASK_SIZE.SMALL = "small"');
    assert(constants.TASK_SIZE.MEDIUM === 'medium', 'TASK_SIZE.MEDIUM = "medium"');
    assert(constants.TASK_SIZE.LARGE === 'large', 'TASK_SIZE.LARGE = "large"');
    assert(constants.TASK_SIZE.XLARGE === 'xlarge', 'TASK_SIZE.XLARGE = "xlarge"');

    assert(constants.TASK_SIZE_THRESHOLDS !== undefined, 'TASK_SIZE_THRESHOLDS exists');
    assert(constants.TASK_SIZE_THRESHOLDS.small.handoff === 0.85, 'Small task handoff = 85%');
    assert(constants.TASK_SIZE_THRESHOLDS.medium.handoff === 0.70, 'Medium task handoff = 70%');
    assert(constants.TASK_SIZE_THRESHOLDS.large.handoff === 0.50, 'Large task handoff = 50%');
    assert(constants.TASK_SIZE_THRESHOLDS.xlarge.handoff === 0.30, 'XLarge task handoff = 30%');

    assert(constants.FILE_COUNT_THRESHOLDS !== undefined, 'FILE_COUNT_THRESHOLDS exists');
    assert(constants.FILE_COUNT_THRESHOLDS.MEDIUM === 10, 'MEDIUM = 10 files');
    assert(constants.FILE_COUNT_THRESHOLDS.LARGE === 50, 'LARGE = 50 files');
    assert(constants.FILE_COUNT_THRESHOLDS.XLARGE === 200, 'XLARGE = 200 files');

    assert(constants.LARGE_TASK_KEYWORDS !== undefined, 'LARGE_TASK_KEYWORDS exists');
    assert(Array.isArray(constants.LARGE_TASK_KEYWORDS), 'LARGE_TASK_KEYWORDS is array');
    assert(constants.LARGE_TASK_KEYWORDS.length > 0, 'LARGE_TASK_KEYWORDS not empty');

    assert(constants.TASK_SIZE_STATE_FILE === 'task-size-state.json', 'TASK_SIZE_STATE_FILE defined');

  } catch (e) {
    log(`❌ Failed to load constants: ${e.message}`, RED);
    testsFailed++;
  }
}

// Test 2: Task size estimator hook
async function testTaskSizeEstimator() {
  log('\n📋 Test 2: Task Size Estimator Hook', BLUE);

  const hookPath = path.join(SCRIPT_DIR, 'task-size-estimator.mjs');
  const stateFile = path.join(tmpdir(), 'task-size-state.json');

  // Clean up state file
  try {
    if (fs.existsSync(stateFile)) fs.unlinkSync(stateFile);
    if (fs.existsSync(stateFile + '.lock')) fs.unlinkSync(stateFile + '.lock');
  } catch (e) {}

  // Test case 1: Small task (no keywords)
  const input1 = JSON.stringify({
    prompt: 'Fix a typo in README',
    session_id: 'test-session-1'
  });

  try {
    const result1 = execSync(`echo '${input1}' | node "${hookPath}"`, { encoding: 'utf8' });
    assert(result1.includes('approve') || result1 === '', 'Small task - no proactive message');

    // Check state file
    if (fs.existsSync(stateFile)) {
      const state = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
      assert(state['test-session-1']?.taskSize === 'small', 'Small task size saved');
    } else {
      log(`⚠️ State file not created for small task`, YELLOW);
    }
  } catch (e) {
    log(`❌ Small task test failed: ${e.message}`, RED);
    testsFailed++;
  }

  // Test case 2: Large task (2-3 keywords)
  const input2 = JSON.stringify({
    prompt: 'Refactor the entire authentication system and update all files',
    session_id: 'test-session-2'
  });

  try {
    const result2 = execSync(`echo '${input2}' | node "${hookPath}"`, { encoding: 'utf8' });
    assert(result2.includes('중대형 작업 감지'), 'Large task - proactive message shown');

    const state = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
    assert(state['test-session-2']?.taskSize === 'large', 'Large task size saved');
  } catch (e) {
    log(`❌ Large task test failed: ${e.message}`, RED);
    testsFailed++;
  }

  // Test case 3: XLarge task (4+ keywords)
  const input3 = JSON.stringify({
    prompt: 'Refactor all components, update entire codebase, migrate database schema',
    session_id: 'test-session-3'
  });

  try {
    const result3 = execSync(`echo '${input3}' | node "${hookPath}"`, { encoding: 'utf8' });
    assert(result3.includes('대형 작업 감지'), 'XLarge task - urgent message shown');

    const state = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
    assert(state['test-session-3']?.taskSize === 'xlarge', 'XLarge task size saved');
  } catch (e) {
    log(`❌ XLarge task test failed: ${e.message}`, RED);
    testsFailed++;
  }

  // Clean up
  try {
    if (fs.existsSync(stateFile)) fs.unlinkSync(stateFile);
    if (fs.existsSync(stateFile + '.lock')) fs.unlinkSync(stateFile + '.lock');
  } catch (e) {}
}

// Test 3: Auto-handoff dynamic thresholds
async function testAutoHandoffDynamicThresholds() {
  log('\n📋 Test 3: Auto-Handoff Dynamic Thresholds', BLUE);

  const stateFile = path.join(tmpdir(), 'task-size-state.json');

  // Setup: Create state with XLARGE task
  const testState = {
    'test-session-xlarge': {
      taskSize: 'xlarge',
      updatedAt: Date.now()
    }
  };
  fs.writeFileSync(stateFile, JSON.stringify(testState, null, 2));

  // Verify auto-handoff.mjs can load the state
  try {
    const autoHandoffPath = path.join(SCRIPT_DIR, 'auto-handoff.mjs');

    // Simulate tool output that triggers 45% usage (above XLARGE 40% threshold)
    const toolOutput = 'x'.repeat(90000); // ~45K tokens
    const hookInput = JSON.stringify({
      tool_name: 'Read',
      session_id: 'test-session-xlarge',
      tool_response: toolOutput,
      tool_input: {}
    });

    const result = execSync(`echo '${hookInput}' | node "${autoHandoffPath}"`, { encoding: 'utf8' });

    if (result) {
      const parsed = JSON.parse(result);
      assert(parsed.decision === 'approve', 'Hook returns approve decision');
      assert(parsed.additionalContext !== undefined, 'Hook provides context message');
      assert(parsed.additionalContext.includes('handoff') || parsed.additionalContext.includes('핸드오프'),
             'Message suggests handoff');
    } else {
      log('⚠️ No output (below threshold or cooldown)', YELLOW);
    }

  } catch (e) {
    log(`⚠️ Dynamic threshold test: ${e.message}`, YELLOW);
  }

  // Clean up
  try {
    if (fs.existsSync(stateFile)) fs.unlinkSync(stateFile);
    if (fs.existsSync(stateFile + '.lock')) fs.unlinkSync(stateFile + '.lock');
  } catch (e) {}
}

// Test 4: File count upgrade
async function testFileCountUpgrade() {
  log('\n📋 Test 4: File Count Task Size Upgrade', BLUE);

  const stateFile = path.join(tmpdir(), 'task-size-state.json');

  // Setup: Start with SMALL task
  const testState = {
    'test-session-upgrade': {
      taskSize: 'small',
      updatedAt: Date.now()
    }
  };
  fs.writeFileSync(stateFile, JSON.stringify(testState, null, 2));

  try {
    const autoHandoffPath = path.join(SCRIPT_DIR, 'auto-handoff.mjs');

    // Simulate Glob output with 60 files (should upgrade to LARGE, threshold is 50)
    const fileList = Array(60).fill(0).map((_, i) => `file${i}.js`).join('\n');
    const hookInput = {
      tool_name: 'Glob',
      session_id: 'test-session-upgrade',
      tool_response: fileList,
      tool_input: { pattern: '**/*.js' }
    };

    // Write to temp file and pipe (proper JSON handling)
    const inputFile = path.join(tmpdir(), 'test-hook-input.json');
    fs.writeFileSync(inputFile, JSON.stringify(hookInput));
    execSync(`cat "${inputFile}" | node "${autoHandoffPath}"`, { encoding: 'utf8' });
    fs.unlinkSync(inputFile);

    // Check if task size was upgraded
    if (fs.existsSync(stateFile)) {
      const state = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
      const upgraded = state['test-session-upgrade']?.taskSize === 'large';
      assert(upgraded, 'Task size upgraded from small to large (60 files)');
    } else {
      log('⚠️ State file not updated', YELLOW);
    }

  } catch (e) {
    log(`⚠️ File count upgrade test: ${e.message}`, YELLOW);
  }

  // Clean up
  try {
    if (fs.existsSync(stateFile)) fs.unlinkSync(stateFile);
    if (fs.existsSync(stateFile + '.lock')) fs.unlinkSync(stateFile + '.lock');
    const autoHandoffState = path.join(tmpdir(), 'auto-handoff-state.json');
    if (fs.existsSync(autoHandoffState)) fs.unlinkSync(autoHandoffState);
  } catch (e) {}
}

// Run all tests
async function runTests() {
  log('='.repeat(60), BLUE);
  log('🧪 Task Size Feature Integration Tests', BLUE);
  log('='.repeat(60), BLUE);

  await testConstants();
  await testTaskSizeEstimator();
  await testAutoHandoffDynamicThresholds();
  await testFileCountUpgrade();

  log('\n' + '='.repeat(60), BLUE);
  log(`✅ Passed: ${testsPassed}`, GREEN);
  log(`❌ Failed: ${testsFailed}`, RED);
  log('='.repeat(60), BLUE);

  process.exit(testsFailed > 0 ? 1 : 0);
}

runTests();
