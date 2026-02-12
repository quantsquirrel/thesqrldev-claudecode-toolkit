<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-11T00:00:00Z | Updated: 2026-02-11T00:00:00Z -->

# mcp/

## Purpose

MCP (Model Context Protocol) server implementation exposing Blueprint tools via JSON-RPC. Provides programmatic read/write access to PDCA cycles, gap analyses, and development pipelines. Enables external tools, scripts, and plugins to query workflow state and advance phases without direct file manipulation.

## Key Files

| File | Description |
|------|-------------|
| `blueprint-server.cjs` | JSON-RPC MCP server (13KB); CommonJS format for Node.js compatibility. Exposes 4 tools: `pdca_status`, `gap_measure`, `pipeline_progress`, and phase advancement methods |

## Subdirectories

None

## For AI Agents

### Working In This Directory

- **CommonJS format**: Use `.cjs` extension (required for MCP server compatibility with Node.js)
- **No dependencies**: Implements MCP protocol using only Node.js built-ins (`fs`, `path`, `readline`)
- **Stdio JSON-RPC**: Server communicates via stdin/stdout; Claude Code launcher manages process
- **Stateless design**: Server reads from `.blueprint/` directory; does not maintain in-memory state
- **Concurrent requests**: Multiple tools can query state simultaneously without blocking
- **Error handling**: All tool methods must return MCP-compliant error responses
- **Process lifecycle**: Server runs for entire Claude Code session; session-end hook triggers graceful shutdown

### Testing Requirements

- **Manual testing**: Start server and send JSON-RPC requests via stdin:
  ```bash
  node blueprint-server.cjs < test-requests.jsonl
  ```
- **Tool verification**: Test all 4 tools with sample state files in `.blueprint/`
- **Concurrent requests**: Simulate multiple simultaneous tool calls
- **Error handling**: Test with missing/corrupted state files; verify error responses
- **State reads**: Verify server correctly parses and returns cycle/pipeline/gap state
- **Integration**: Test with Claude Code MCP loader (automatic at session start)

### Common Patterns

- **Tool naming**: Snake_case for tool names; tool methods implement MCP `tool` schema
- **State file discovery**: Use `findBlueprintRoot()` to locate `.blueprint/` directory
- **Locking awareness**: Server does NOT acquire locks (read-only); respects lock files created by state manager
- **Response format**: All tools must return `{ success: true, data: {...} }` or `{ success: false, error: "..." }`
- **Buffered updates**: `pdca_update` and `pipeline_advance` write to `pending_updates.json` (NOT directly to state files)

## Dependencies

### Internal

- `.blueprint/` directory - reads cycle, pipeline, and gap state files
- `pending_updates.json` - buffered write queue for non-query operations
- Root `mcp/` directory reference in `.mcp.json` (plugin root)

### External

- **Zero npm dependencies** - uses only Node.js built-ins:
  - `fs` - File I/O
  - `path` - Path manipulation
  - `readline` - Stdio communication
  - `crypto` - Request ID generation (optional)

## MCP Protocol Implementation

**Tools exposed:**

1. **pdca_status** (read-only)
   - Input: `{ cycle_id?: string }`
   - Output: PDCA cycle state (ID, phase, iteration, progress, phase timeline)
   - Use case: Query active PDCA cycles

2. **gap_measure** (read-only)
   - Input: `{ analysis_id?: string }`
   - Output: Gap metrics (severity distribution, closure rate, recommendations)
   - Use case: Measure gap analysis progress

3. **pipeline_progress** (read-only)
   - Input: `{ run_id?: string }`
   - Output: Pipeline state (current phase, gates passed, phase ETA, completion %)
   - Use case: Check pipeline execution progress

4. **pdca_update** (write via buffer)
   - Input: `{ cycle_id: string, phase: string, status: string }`
   - Output: Confirmation
   - Use case: Advance PDCA phase (buffered; processed by hooks)

5. **pipeline_advance** (write via buffer)
   - Input: `{ run_id: string, next_phase: string }`
   - Output: Confirmation
   - Use case: Advance pipeline to next phase (buffered; processed by hooks)

**Communication:**
- Stdin: Client sends JSON-RPC requests (method, params, id)
- Stdout: Server responds with JSON-RPC results (id, result/error)
- Protocol: Line-delimited JSON (one request/response per line)

## Integration with Claude Code

**Lifecycle:**
1. Claude Code loads `.mcp.json` at session start
2. Spawns `node blueprint-server.cjs` as subprocess
3. Connects stdin/stdout for JSON-RPC communication
4. Registers 5 tools in MCP tool catalog
5. Agents/skills query tools via MCP (same as other MCP tools like GitHub, Tavily)
6. Session-end hook sends SIGTERM to gracefully stop server

**Invocation from agents:**
```
Use the MCP tool: mcp__plugin_blueprint_blueprint__pdca_status
Parameters: { "cycle_id": "..." }
```

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
