<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-11T00:00:00Z | Updated: 2026-02-11T00:00:00Z -->

# config/

## Purpose

JSON configuration files for customizing Blueprint workflow behavior. Control PDCA cycle parameters, pipeline phase definitions, and per-project agent model overrides. Edit these files to adjust timeouts, iteration limits, phase sequences, or assign different agents to phases.

## Key Files

| File | Description |
|------|-------------|
| `pdca-defaults.json` | PDCA cycle configuration (iteration limits, timeouts, agent assignments per phase) |
| `pipeline-phases.json` | Pipeline phase definitions (9 phases with gates, presets for full/standard/minimal workflows) |
| `agent-overrides.json` | Per-project agent overrides (model assignment, enable/disable per agent, fallback strategy) |

## Configuration Reference

### pdca-defaults.json

```json
{
  "max_iterations": 4,           // Maximum PDCA cycles (default 4, range 1-10)
  "phase_timeout_ms": 300000,    // Per-phase timeout in ms (default 5 min)
  "auto_act": false,             // Auto-proceed to Act after Check (default false)
  "default_agents": {
    "plan": ["blueprint:analyst", "blueprint:pdca-iterator"],
    "do": ["blueprint:executor"],
    "check": ["blueprint:verifier"],
    "act": ["blueprint:pdca-iterator"]
  }
}
```

**Customization:**
- Increase `max_iterations` for complex problems requiring multiple refinement cycles
- Lower `phase_timeout_ms` for faster workflows (risks timeouts on slow agents)
- Set `auto_act: true` to skip user confirmation after Check phase
- Override `default_agents` to use different agents per phase

### pipeline-phases.json

9 phases (index 0-8):

```json
{
  "phases": [
    {"index": 0, "name": "requirements", "agent": "blueprint:analyst", "gate": "requirements document exists"},
    {"index": 1, "name": "architecture", "agent": "blueprint:architect", "gate": "architecture decision recorded"},
    {"index": 2, "name": "design", "agent": "blueprint:design-writer", "gate": "design document exists"},
    {"index": 3, "name": "implementation", "agent": "blueprint:executor", "gate": "code changes committed"},
    {"index": 4, "name": "unit-test", "agent": "blueprint:tester", "gate": "unit tests pass"},
    {"index": 5, "name": "integration-test", "agent": "blueprint:tester", "gate": "integration tests pass"},
    {"index": 6, "name": "code-review", "agent": "blueprint:reviewer", "gate": "review approved"},
    {"index": 7, "name": "gap-analysis", "agent": "blueprint:gap-detector", "gate": "no critical gaps"},
    {"index": 8, "name": "verification", "agent": "blueprint:verifier", "gate": "all checks pass"}
  ],
  "presets": {
    "full": {"phases": [0,1,2,3,4,5,6,7,8], "description": "Full 9-stage pipeline"},
    "standard": {"phases": [0,2,3,4,6,8], "description": "Standard 6-stage (skip arch, integration-test, gap-analysis)"},
    "minimal": {"phases": [2,3,8], "description": "Minimal 3-stage (design, implementation, verification)"},
    "auto": {"phases": null, "description": "Auto-detect based on workspace complexity"}
  },
  "defaults": {
    "preset": "auto",
    "on_error": "pause",
    "max_retries": 2
  }
}
```

**Phase Gates:**
- `"all checks pass"` - generic gate (verifier decides specifics)
- `"code changes committed"` - git status must be clean after phase
- `"tests pass"` - test runner exit code 0
- Custom gates: phases define their own success criteria

**Presets:**
- `full` - All 9 phases (exhaustive workflow)
- `standard` - 6 phases (skip architecture, integration test, gap analysis for fast iteration)
- `minimal` - 3 phases (design → implement → verify, minimal overhead)
- `auto` - Detect based on codebase complexity (new feature vs refactor vs bug fix)

**Customization:**
- Add/remove phases: modify `phases` array
- Change agent: update `"agent"` field per phase
- Create custom preset: add to `presets` object
- Skip phases: in `presets[preset].phases`, omit phase indices

### agent-overrides.json

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$comment": "Per-project agent override configuration",
  "overrides": {
    "analyst": {"model": "opus", "enabled": true},
    "architect": {"model": "opus", "enabled": true},
    "design-writer": {"model": "sonnet", "enabled": true},
    "executor": {"model": "sonnet", "enabled": true},
    "gap-detector": {"model": "opus", "enabled": true},
    "pdca-iterator": {"model": "sonnet", "enabled": true},
    "reviewer": {"model": "sonnet", "enabled": true},
    "tester": {"model": "sonnet", "enabled": true},
    "verifier": {"model": "sonnet", "enabled": true}
  },
  "fallback": "inline-prompt"
}
```

**Customization:**
- Change `model` to use faster (haiku) or more powerful (opus) models per agent
- Set `enabled: false` to skip an agent in pipeline
- `fallback` controls behavior if plugin agent unavailable:
  - `"inline-prompt"` - use inline prompt from skill handler (default)
  - `"error"` - fail workflow if agent unavailable

## For AI Agents

### Working In This Directory

- **Schema validation**: All JSON files follow JSON Schema Draft 2020-12
- **No code**: Config files are data only, no executable content
- **Runtime reload**: Hooks read config on every invocation (safe to edit mid-workflow)
- **Preset expansion**: `presets.auto` is computed at runtime based on workspace analysis

### Testing Requirements

- Test invalid JSON: verify error handling when JSON is malformed
- Test phase gates: verify each phase waits for its gate condition
- Test preset expansion: verify `auto` preset produces correct phase sequence
- Test agent override: change model for one agent, verify it's used in workflow
- Test disable/enable: set `enabled: false` for agent, verify phase is skipped

### Common Patterns

- **Gate evaluation**: Custom gates are evaluated by phase agents (they decide what "pass" means)
- **Timeout handling**: Phase timeout triggers automatic `on_error` action (pause/retry/fail)
- **Retry logic**: `max_retries` applies per phase, not per cycle

## Dependencies

### Internal

- Hooks read pdca-defaults.json and pipeline-phases.json on initialization
- MCP tools read config to generate phase metadata
- Skills expand presets and validate config on workflow start

### External

None - static JSON configuration.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
