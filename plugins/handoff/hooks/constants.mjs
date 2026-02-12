/**
 * Auto-Handoff Hook Constants
 *
 * Thresholds and messages for context usage monitoring.
 * Triggers handoff suggestion when context reaches 70%.
 */

/**
 * Threshold ratio to trigger handoff suggestion (70%)
 */
export const HANDOFF_THRESHOLD = 0.70;

/**
 * Warning threshold (80%) - more urgent suggestion
 */
export const WARNING_THRESHOLD = 0.80;

/**
 * Critical threshold (90%) - immediate handoff needed
 */
export const CRITICAL_THRESHOLD = 0.90;

/**
 * Cooldown period between handoff suggestions (3 minutes)
 */
export const HANDOFF_COOLDOWN_MS = 180_000;

/**
 * Maximum suggestions per session
 */
export const MAX_SUGGESTIONS = 2;

/**
 * Default context limit for Claude models
 */
export const CLAUDE_CONTEXT_LIMIT =
  process.env.ANTHROPIC_1M_CONTEXT === 'true' ||
  process.env.VERTEX_ANTHROPIC_1M_CONTEXT === 'true'
    ? 1_000_000
    : 200_000;

/**
 * Average characters per token estimate
 */
export const CHARS_PER_TOKEN = 4;

/**
 * Handoff suggestion message (70% threshold)
 */
export const HANDOFF_SUGGESTION_MESSAGE = `📋 HANDOFF SUGGESTION - Context 70%+ Reached

Your context usage is getting high. Consider creating a handoff to preserve your work:

  /handoff "current-task-topic"

This will:
✅ Save all progress and decisions
✅ Copy summary to clipboard
✅ Enable seamless session resume

Tip: Create handoffs before context gets too high to capture full context.
`;

/**
 * Warning message (80% threshold)
 */
export const HANDOFF_WARNING_MESSAGE = `⚠️ HANDOFF RECOMMENDED - Context 80%+ Reached

Context space is running low. Strongly recommended to create a handoff now:

  /handoff "current-task-topic"

Benefits:
• Preserve all decisions and failed approaches
• Quality score validates completeness
• Clipboard-ready for next session

Action: Run /handoff soon to avoid losing context.
`;

/**
 * Critical message (90% threshold)
 */
export const HANDOFF_CRITICAL_MESSAGE = `🚨 HANDOFF URGENT - Context 90%+ Reached

Context is almost full. Create a handoff immediately:

  /handoff "current-task-topic"

Without a handoff:
❌ Progress may be lost
❌ Next session starts from scratch
❌ Decisions need re-explaining

Action required: Run /handoff NOW before context overflow.
`;

/**
 * Auto-draft feature enabled
 */
export const AUTO_DRAFT_ENABLED = true;

/**
 * Draft file prefix
 */
export const DRAFT_FILE_PREFIX = '.draft-';

/**
 * Lock file name
 */
export const LOCK_FILE_NAME = '.generating.lock';

// ==========================================
// Task Size Classification (v2.0)
// ==========================================

/**
 * Task size categories
 */
export const TASK_SIZE = {
  SMALL: 'small',
  MEDIUM: 'medium',
  LARGE: 'large',
  XLARGE: 'xlarge',
};

/**
 * Keywords indicating large tasks
 */
export const LARGE_TASK_KEYWORDS = [
  '전체', '모든', 'all', 'every',
  '리팩토링', 'refactor', 'refactoring',
  '마이그레이션', 'migrate', 'migration',
  'autopilot', 'ultrawork', 'ralph',
  '대규모', 'massive', 'entire',
];

/**
 * Dynamic thresholds per task size
 */
export const TASK_SIZE_THRESHOLDS = {
  [TASK_SIZE.SMALL]: { handoff: 0.85, warning: 0.90, critical: 0.95 },
  [TASK_SIZE.MEDIUM]: { handoff: 0.70, warning: 0.80, critical: 0.90 },
  [TASK_SIZE.LARGE]: { handoff: 0.50, warning: 0.60, critical: 0.70 },
  [TASK_SIZE.XLARGE]: { handoff: 0.30, warning: 0.40, critical: 0.50 },
};

/**
 * File count thresholds for task size upgrade
 */
export const FILE_COUNT_THRESHOLDS = {
  MEDIUM: 10,   // 10+ files
  LARGE: 50,    // 50+ files
  XLARGE: 200,  // 200+ files
};

/**
 * Task size state file
 */
export const TASK_SIZE_STATE_FILE = 'task-size-state.json';

// ==========================================
// Security Patterns (Synod Recommendation)
// ==========================================

/**
 * Enhanced security patterns for detecting and masking sensitive data.
 * These patterns help prevent accidental exposure of credentials, tokens, and secrets.
 *
 * @type {RegExp[]}
 */
export const SECURITY_PATTERNS = [
  // JWT tokens
  /eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g,
  // Base64 encoded secrets (40+ chars)
  /[A-Za-z0-9+/]{40,}={0,2}/g,
  // Environment variable references
  /process\.env\.[A-Z_]+/g,
  // Bearer tokens
  /Bearer\s+[^\s]+/gi,
  // AWS Access Keys
  /AKIA[0-9A-Z]{16}/g,
  // Generic API keys
  /[a-zA-Z0-9_-]*(?:api[_-]?key|apikey|secret|token|password|credential)[a-zA-Z0-9_-]*\s*[:=]\s*['"]?[^\s'"]+/gi,
];

/**
 * Safe key names for JSON schema.
 * Defines allowed keys and forbidden patterns to prevent sensitive data in key names.
 *
 * @type {Object}
 * @property {string[]} ALLOWED_KEYS - Whitelisted key names for handoff documents
 * @property {RegExp[]} FORBIDDEN_PATTERNS - Patterns that should not appear in key names
 */
export const SAFE_KEY_SCHEMA = {
  ALLOWED_KEYS: ['topic', 'summary', 'files', 'decisions', 'approaches', 'next_step'],
  FORBIDDEN_PATTERNS: [/password/i, /secret/i, /key/i, /token/i, /credential/i, /ssn/i, /email/i],
};

/**
 * Masks sensitive data in text using predefined security patterns.
 *
 * @param {string} text - Text to mask
 * @returns {string} Text with sensitive data replaced with '***REDACTED***'
 *
 * @example
 * maskSensitiveData('Bearer abc123xyz')
 * // Returns: '***REDACTED***'
 *
 * @example
 * maskSensitiveData('API_KEY=secret123')
 * // Returns: '***REDACTED***'
 */
export function maskSensitiveData(text) {
  let masked = text;
  for (const pattern of SECURITY_PATTERNS) {
    masked = masked.replace(pattern, '***REDACTED***');
  }
  return masked;
}

/**
 * Validates if a key name is safe and doesn't contain forbidden patterns.
 *
 * @param {string} keyName - Key name to validate
 * @returns {boolean} True if key name is safe, false if it contains forbidden patterns
 *
 * @example
 * validateKeyName('topic')
 * // Returns: true
 *
 * @example
 * validateKeyName('user_password')
 * // Returns: false
 */
export function validateKeyName(keyName) {
  return !SAFE_KEY_SCHEMA.FORBIDDEN_PATTERNS.some(p => p.test(keyName));
}
