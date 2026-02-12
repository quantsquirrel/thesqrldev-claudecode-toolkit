#!/usr/bin/env node
"use strict";

/**
 * Blueprint Helix MCP Server
 *
 * Provides read and write access to PDCA cycles, gap analyses, and pipeline runs
 * via Model Context Protocol (MCP) over stdio JSON-RPC.
 *
 * Tools:
 * - pdca_status: Query PDCA cycle status
 * - gap_measure: Measure gap analysis metrics
 * - pipeline_progress: Check development pipeline progress
 * - pdca_update: Update PDCA cycle phase or status (buffered)
 * - pipeline_advance: Advance pipeline to next phase or update status (buffered)
 */

const fs = require('fs');
const path = require('path');
const readline = require('readline');

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Find .blueprint/ directory by walking up from cwd.
 * @returns {string|null} Absolute path to .blueprint/ or null if not found
 */
function findBlueprintRoot() {
  let dir = process.cwd();
  const root = path.parse(dir).root;

  while (dir !== root) {
    const bpPath = path.join(dir, '.blueprint');
    if (fs.existsSync(bpPath)) {
      return bpPath;
    }
    if (fs.existsSync(path.join(dir, '.git'))) {
      return bpPath;
    }
    dir = path.dirname(dir);
  }

  // Fallback: use cwd
  return path.join(process.cwd(), '.blueprint');
}

/**
 * Load and parse a JSON file.
 * @param {string} filePath - Absolute path to JSON file
 * @returns {object|null} Parsed data or null if not found/invalid
 */
function loadState(filePath) {
  try {
    const raw = fs.readFileSync(filePath, 'utf-8');
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/**
 * List all JSON files in a directory.
 * @param {string} dirPath - Absolute directory path
 * @returns {string[]} Array of absolute file paths
 */
function listJsonFiles(dirPath) {
  try {
    if (!fs.existsSync(dirPath)) {
      return [];
    }
    const entries = fs.readdirSync(dirPath);
    return entries
      .filter(name => name.endsWith('.json'))
      .map(name => path.join(dirPath, name));
  } catch {
    return [];
  }
}

// ============================================================================
// MCP Tool Implementations
// ============================================================================

/**
 * Write a pending update to the buffer file.
 * @param {string} type - 'pdca' or 'pipeline'
 * @param {object} update - Update data
 */
function writePendingUpdate(type, update) {
  const bpRoot = findBlueprintRoot();
  const pendingPath = path.join(bpRoot, 'pending_updates.json');

  let pending = [];
  try {
    const raw = fs.readFileSync(pendingPath, 'utf-8');
    pending = JSON.parse(raw);
    if (!Array.isArray(pending)) pending = [];
  } catch { /* file doesn't exist yet */ }

  pending.push({
    type,
    timestamp: new Date().toISOString(),
    ...update
  });

  fs.mkdirSync(bpRoot, { recursive: true });
  fs.writeFileSync(pendingPath, JSON.stringify(pending, null, 2) + '\n', 'utf-8');
}

/**
 * Tool: pdca_status
 * Query the current PDCA cycle status.
 * @param {object} args - { cycle_id?: string }
 * @returns {object} { cycles: [...] }
 */
function pdcaStatus(args) {
  const bpRoot = findBlueprintRoot();
  const cyclesDir = path.join(bpRoot, 'pdca', 'cycles');

  const cycles = [];
  const files = listJsonFiles(cyclesDir);

  for (const filePath of files) {
    const data = loadState(filePath);
    if (!data) continue;

    // Filter by cycle_id if provided
    if (args.cycle_id && data.id !== args.cycle_id) {
      continue;
    }

    cycles.push({
      id: data.id || path.basename(filePath, '.json'),
      phase: data.phase || 'plan',
      iteration: data.iteration || 1,
      max_iterations: data.max_iterations || 3,
      status: data.status || 'active',
      created_at: data.created_at || data.createdAt || null,
      updated_at: data.updated_at || data.updatedAt || null
    });
  }

  return { cycles };
}

/**
 * Tool: gap_measure
 * Measure gap analysis metrics.
 * @param {object} args - { analysis_id?: string }
 * @returns {object} { analyses: [...] }
 */
function gapMeasure(args) {
  const bpRoot = findBlueprintRoot();
  const analysesDir = path.join(bpRoot, 'gaps', 'analyses');

  const analyses = [];
  const files = listJsonFiles(analysesDir);

  for (const filePath of files) {
    const data = loadState(filePath);
    if (!data) continue;

    // Filter by analysis_id if provided
    if (args.analysis_id && data.id !== args.analysis_id) {
      continue;
    }

    // Count gaps by severity
    const gaps = data.gaps || [];
    const bySeverity = {
      critical: 0,
      high: 0,
      medium: 0,
      low: 0
    };

    for (const gap of gaps) {
      const severity = (gap.severity || 'low').toLowerCase();
      if (bySeverity.hasOwnProperty(severity)) {
        bySeverity[severity]++;
      }
    }

    // Calculate closure rate
    const totalGaps = gaps.length;
    const closedGaps = gaps.filter(g => g.status === 'closed' || g.resolved).length;
    const closureRate = totalGaps > 0 ? (closedGaps / totalGaps) * 100 : 0;

    analyses.push({
      id: data.id || path.basename(filePath, '.json'),
      total_gaps: totalGaps,
      by_severity: bySeverity,
      closure_rate: Math.round(closureRate * 100) / 100
    });
  }

  return { analyses };
}

/**
 * Tool: pipeline_progress
 * Check development pipeline progress.
 * @param {object} args - { run_id?: string }
 * @returns {object} { pipelines: [...] }
 */
function pipelineProgress(args) {
  const bpRoot = findBlueprintRoot();
  const runsDir = path.join(bpRoot, 'pipeline', 'runs');

  const pipelines = [];
  const files = listJsonFiles(runsDir);

  for (const filePath of files) {
    const data = loadState(filePath);
    if (!data) continue;

    // Filter by run_id if provided
    if (args.run_id && data.id !== args.run_id) {
      continue;
    }

    const phases = data.phases || [];
    const totalPhases = phases.length;
    const currentPhaseIndex = data.current_phase_index || 0;
    const currentPhaseName = phases[currentPhaseIndex]?.name || 'unknown';

    pipelines.push({
      id: data.id || path.basename(filePath, '.json'),
      preset: data.preset || 'standard',
      current_phase: currentPhaseName,
      total_phases: totalPhases,
      status: data.status || 'running',
      phases: phases.map(p => ({
        name: p.name || 'unnamed',
        status: p.status || 'pending'
      }))
    });
  }

  return { pipelines };
}

/**
 * Tool: pdca_update
 * Update PDCA cycle phase or status.
 * @param {object} args - { cycle_id, phase?, status?, notes? }
 * @returns {object} { success, message, pending_update }
 */
function pdcaUpdate(args) {
  const update = {
    cycle_id: args.cycle_id,
    ...(args.phase && { phase: args.phase }),
    ...(args.status && { status: args.status }),
    ...(args.notes && { notes: args.notes })
  };

  writePendingUpdate('pdca', update);

  return {
    success: true,
    message: `PDCA update queued for cycle ${args.cycle_id}`,
    pending_update: update
  };
}

/**
 * Tool: pipeline_advance
 * Advance pipeline to next phase or update phase status.
 * @param {object} args - { run_id, action, phase_output?, notes? }
 * @returns {object} { success, message, pending_update }
 */
function pipelineAdvance(args) {
  const update = {
    run_id: args.run_id,
    action: args.action,
    ...(args.phase_output && { phase_output: args.phase_output }),
    ...(args.notes && { notes: args.notes })
  };

  writePendingUpdate('pipeline', update);

  return {
    success: true,
    message: `Pipeline ${args.action} queued for run ${args.run_id}`,
    pending_update: update
  };
}

// ============================================================================
// MCP Server Protocol
// ============================================================================

const TOOLS = [
  {
    name: 'pdca_status',
    description: 'Query the current PDCA cycle status',
    inputSchema: {
      type: 'object',
      properties: {
        cycle_id: {
          type: 'string',
          description: 'Optional: specific cycle ID to query'
        }
      }
    }
  },
  {
    name: 'gap_measure',
    description: 'Measure gap analysis metrics',
    inputSchema: {
      type: 'object',
      properties: {
        analysis_id: {
          type: 'string',
          description: 'Optional: specific analysis ID to query'
        }
      }
    }
  },
  {
    name: 'pipeline_progress',
    description: 'Check development pipeline progress',
    inputSchema: {
      type: 'object',
      properties: {
        run_id: {
          type: 'string',
          description: 'Optional: specific pipeline run ID to query'
        }
      }
    }
  },
  {
    name: 'pdca_update',
    description: 'Update PDCA cycle phase or status. Writes to pending buffer for safe merge.',
    inputSchema: {
      type: 'object',
      properties: {
        cycle_id: { type: 'string', description: 'PDCA cycle ID to update' },
        phase: { type: 'string', enum: ['plan', 'do', 'check', 'act'], description: 'New phase' },
        status: { type: 'string', enum: ['active', 'paused', 'completed', 'failed'], description: 'New status' },
        notes: { type: 'string', description: 'Optional notes for this update' }
      },
      required: ['cycle_id']
    }
  },
  {
    name: 'pipeline_advance',
    description: 'Advance pipeline to next phase or update phase status. Writes to pending buffer for safe merge.',
    inputSchema: {
      type: 'object',
      properties: {
        run_id: { type: 'string', description: 'Pipeline run ID' },
        action: { type: 'string', enum: ['advance', 'complete_phase', 'fail_phase', 'pause', 'resume'], description: 'Action to take' },
        phase_output: { type: 'string', description: 'Output/summary from the completed phase' },
        notes: { type: 'string', description: 'Optional notes' }
      },
      required: ['run_id', 'action']
    }
  }
];

/**
 * Handle JSON-RPC request.
 * @param {object} request - Parsed JSON-RPC request
 * @returns {object|null} JSON-RPC response or null for notifications
 */
function handleRequest(request) {
  const { jsonrpc, id, method, params } = request;

  // Ignore notifications (no id field)
  if (id === undefined) {
    return null;
  }

  try {
    switch (method) {
      case 'initialize':
        return {
          jsonrpc: '2.0',
          id,
          result: {
            protocolVersion: '2024-11-05',
            serverInfo: {
              name: 'blueprint',
              version: '1.0.0'
            },
            capabilities: {
              tools: {}
            }
          }
        };

      case 'tools/list':
        return {
          jsonrpc: '2.0',
          id,
          result: {
            tools: TOOLS
          }
        };

      case 'tools/call':
        const { name, arguments: args = {} } = params || {};
        let toolResult;

        switch (name) {
          case 'pdca_status':
            toolResult = pdcaStatus(args);
            break;
          case 'gap_measure':
            toolResult = gapMeasure(args);
            break;
          case 'pipeline_progress':
            toolResult = pipelineProgress(args);
            break;
          case 'pdca_update':
            toolResult = pdcaUpdate(args);
            break;
          case 'pipeline_advance':
            toolResult = pipelineAdvance(args);
            break;
          default:
            throw new Error(`Unknown tool: ${name}`);
        }

        return {
          jsonrpc: '2.0',
          id,
          result: {
            content: [
              {
                type: 'text',
                text: JSON.stringify(toolResult, null, 2)
              }
            ]
          }
        };

      default:
        throw new Error(`Unknown method: ${method}`);
    }
  } catch (error) {
    return {
      jsonrpc: '2.0',
      id,
      error: {
        code: -32603,
        message: error.message || 'Internal error'
      }
    };
  }
}

/**
 * Main server loop: read JSON-RPC from stdin, write responses to stdout.
 */
function main() {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false
  });

  rl.on('line', (line) => {
    try {
      const request = JSON.parse(line);
      const response = handleRequest(request);

      if (response) {
        console.log(JSON.stringify(response));
      }
    } catch (error) {
      // Invalid JSON or parsing error
      console.error(JSON.stringify({
        jsonrpc: '2.0',
        id: null,
        error: {
          code: -32700,
          message: 'Parse error'
        }
      }));
    }
  });

  rl.on('close', () => {
    process.exit(0);
  });
}

// Start the server
if (require.main === module) {
  main();
}

module.exports = { pdcaStatus, gapMeasure, pipelineProgress, pdcaUpdate, pipelineAdvance };
