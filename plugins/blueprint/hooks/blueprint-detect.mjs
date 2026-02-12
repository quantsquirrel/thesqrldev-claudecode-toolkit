#!/usr/bin/env node

/**
 * Blueprint Detect Hook (UserPromptSubmit)
 * Detects /blueprint:pdca, /blueprint:gap, /blueprint:pipeline, /blueprint:cancel keywords
 * and emits additionalContext to instruct Claude on the detected mode.
 *
 * Pattern: blueprint keyword-detector
 */

import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { readStdin } from './lib/io.mjs';
import { error, info } from './lib/logger.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Extract prompt from various JSON structures
function extractPrompt(input) {
  try {
    const data = JSON.parse(input);
    if (data.prompt) return data.prompt;
    if (data.message?.content) return data.message.content;
    if (Array.isArray(data.parts)) {
      return data.parts.filter(p => p.type === 'text').map(p => p.text).join(' ');
    }
    return '';
  } catch {
    const match = input.match(/"(?:prompt|content|text)"\s*:\s*"([^"]+)"/);
    return match ? match[1] : '';
  }
}

// Blueprint keyword definitions
const BLUEPRINT_KEYWORDS = [
  {
    name: 'pdca',
    pattern: /\/blueprint:pdca\b/i,
    description: 'PDCA cycle management',
    instruction: `[BLUEPRINT: PDCA CYCLE ACTIVATED]

You are now in PDCA (Plan-Do-Check-Act) cycle mode.

Available operations:
- Start a new PDCA cycle with a clear objective
- Progress through phases: Plan -> Do -> Check -> Act
- Each phase requires explicit completion before moving to the next
- Use state files in .blueprint/pdca/ for tracking

Follow the PDCA methodology strictly:
1. PLAN: Define objectives, metrics, and approach
2. DO: Execute the plan, implement changes
3. CHECK: Verify results against objectives, run tests
4. ACT: Standardize successes, address gaps, iterate`
  },
  {
    name: 'gap',
    pattern: /\/blueprint:gap\b/i,
    description: 'Gap analysis',
    instruction: `[BLUEPRINT: GAP ANALYSIS ACTIVATED]

You are now in Gap Analysis mode.

Available operations:
- Analyze the current state vs. desired state
- Identify gaps with severity levels (critical, high, medium, low)
- Generate reports with actionable recommendations
- Track gap resolution progress

Process:
1. Define the desired/target state
2. Assess the current state
3. Identify and categorize gaps
4. Prioritize by severity and impact
5. Create remediation plan`
  },
  {
    name: 'pipeline',
    pattern: /\/blueprint:pipeline\b/i,
    description: 'Pipeline execution',
    instruction: `[BLUEPRINT: PIPELINE ACTIVATED]

You are now in Pipeline execution mode.

Pipeline phases (full preset):
1. Requirements -> 2. Architecture -> 3. Design -> 4. Implementation
5. Unit Test -> 6. Integration Test -> 7. Code Review -> 8. Gap Analysis -> 9. Verification

Available presets:
- full: All 9 stages
- standard: 6 stages (requirements, design, implementation, unit-test, code-review, verification)
- minimal: 3 stages (design, implementation, verification)

Each phase produces artifacts that feed into the next phase.`
  },
  {
    name: 'cancel',
    pattern: /\/blueprint:cancel\b/i,
    description: 'Cancel active blueprint mode',
    instruction: `[BLUEPRINT: CANCEL]

Cancel the currently active blueprint mode (PDCA cycle, gap analysis, or pipeline).
Archive the current state and clean up active state files.`
  }
];

// Create hook output with additionalContext
function createHookOutput(additionalContext) {
  return {
    continue: true,
    hookSpecificOutput: {
      hookEventName: 'UserPromptSubmit',
      additionalContext
    }
  };
}

async function main() {
  info('blueprint-detect', 'Hook started');
  try {
    const input = await readStdin();
    if (!input.trim()) {
      process.stdout.write(JSON.stringify({ continue: true }));
      return;
    }

    const prompt = extractPrompt(input);
    if (!prompt) {
      process.stdout.write(JSON.stringify({ continue: true }));
      return;
    }

    // Check for blueprint keywords
    const matched = BLUEPRINT_KEYWORDS.find(kw => kw.pattern.test(prompt));

    if (!matched) {
      process.stdout.write(JSON.stringify({ continue: true }));
      return;
    }

    // Parse additional context from prompt (e.g., task description after keyword)
    const afterKeyword = prompt.replace(matched.pattern, '').trim();
    let context = matched.instruction;
    if (afterKeyword) {
      context += `\n\nUser request: ${afterKeyword}`;
    }

    process.stdout.write(JSON.stringify(createHookOutput(context)));
  } catch (err) {
    error('blueprint-detect', `Unexpected error: ${err?.message || err}`, { stack: err?.stack });
    process.stdout.write(JSON.stringify({ continue: true }));
  }
}

main();
