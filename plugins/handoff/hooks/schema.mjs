/**
 * Structured JSON schemas for Claude Code hooks
 *
 * This module defines standardized schemas for hook outputs,
 * particularly for session handoff documents that combine
 * natural language summaries with structured metadata.
 *
 * @module hooks/schema
 */

/**
 * Schema for structured handoff output
 *
 * Combines human-readable natural language summaries with
 * machine-parseable structured data for efficient session
 * context transfer and analysis.
 *
 * @typedef {Object} HandoffSchema
 * @property {Object} summary - Container for summary data
 * @property {string} summary.natural_language - Human-readable summary (200-500 tokens)
 * @property {Object} summary.structured_data - Machine-parseable metadata
 * @property {Array<FileModification>} summary.structured_data.files_modified - Files changed during session
 * @property {Array<FunctionTouch>} summary.structured_data.functions_touched - Functions modified or created
 * @property {Array<FailedApproach>} summary.structured_data.failed_approaches - Attempted approaches that didn't work
 * @property {Array<Decision>} summary.structured_data.decisions - Key architectural or implementation decisions
 */

/**
 * Represents a file modification
 *
 * @typedef {Object} FileModification
 * @property {string} path - Relative path from project root
 * @property {Array<number>} lines - Line numbers modified (empty array for full file operations)
 * @property {'edit'|'create'|'delete'} type - Type of modification
 */

/**
 * Represents a function or method that was touched
 *
 * @typedef {Object} FunctionTouch
 * @property {string} name - Function/method name
 * @property {string} file - File path containing the function
 * @property {string} action - Description of what was done (e.g., "added error handling", "refactored logic")
 */

/**
 * Represents an approach that was tried but failed
 *
 * @typedef {Object} FailedApproach
 * @property {string} approach - Description of the attempted approach
 * @property {string} reason - Why it failed or was rejected
 * @property {Array<string>} files - Files affected during the attempt
 */

/**
 * Represents a key decision made during the session
 *
 * @typedef {Object} Decision
 * @property {string} topic - What decision was about (e.g., "authentication strategy", "state management")
 * @property {string} chosen - The approach that was selected
 * @property {Array<string>} rejected - Alternative approaches considered but not chosen
 * @property {string} rationale - Why this decision was made
 */

/**
 * Standard handoff schema for session context transfer
 *
 * Use this schema as a template when generating handoff documents.
 * The dual format (natural language + structured data) ensures both
 * human readability and machine parseability.
 *
 * Security note: Keys are abstracted and do not expose sensitive
 * information. Actual sensitive data should never be included in
 * handoff documents.
 *
 * @type {HandoffSchema}
 */
export const HANDOFF_SCHEMA = {
  summary: {
    natural_language: "",  // 200-500 token narrative summary
    structured_data: {
      files_modified: [
        // Example:
        // { path: "src/auth.ts", lines: [45, 46, 78], type: "edit" }
      ],
      functions_touched: [
        // Example:
        // { name: "validateToken", file: "src/auth.ts", action: "added JWT validation" }
      ],
      failed_approaches: [
        // Example:
        // {
        //   approach: "Using localStorage for token storage",
        //   reason: "Vulnerable to XSS attacks",
        //   files: ["src/auth.ts"]
        // }
      ],
      decisions: [
        // Example:
        // {
        //   topic: "token storage strategy",
        //   chosen: "httpOnly cookies",
        //   rejected: ["localStorage", "sessionStorage"],
        //   rationale: "Provides XSS protection while maintaining session persistence"
        // }
      ]
    }
  }
};

/**
 * Validates a handoff object against the schema
 *
 * @param {any} handoff - The handoff object to validate
 * @returns {boolean} True if valid, false otherwise
 */
export function validateHandoff(handoff) {
  if (!handoff?.summary) return false;
  if (typeof handoff.summary.natural_language !== 'string') return false;
  if (!handoff.summary.structured_data) return false;

  const { structured_data } = handoff.summary;

  // Validate arrays exist
  if (!Array.isArray(structured_data.files_modified)) return false;
  if (!Array.isArray(structured_data.functions_touched)) return false;
  if (!Array.isArray(structured_data.failed_approaches)) return false;
  if (!Array.isArray(structured_data.decisions)) return false;

  return true;
}

/**
 * Creates an empty handoff object following the schema
 *
 * @returns {HandoffSchema} Empty handoff object
 */
export function createEmptyHandoff() {
  return {
    summary: {
      natural_language: "",
      structured_data: {
        files_modified: [],
        functions_touched: [],
        failed_approaches: [],
        decisions: []
      }
    }
  };
}
