<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-12T00:00:00Z | Updated: 2026-02-12T00:00:00Z -->

# assets/

## Purpose

Visual assets for Blueprint Helix documentation and marketing. Contains hero banner, diagrams, and other graphics used in README files and project documentation.

## Key Files

| File | Description |
|------|-------------|
| `hero-banner.svg` | Animated hero banner (1200×400px) with PDCA cycle, pipeline stages, and feature pills |
| `README.md` | Asset documentation with specifications, usage examples, and design details |

## For AI Agents

### Working In This Directory

- **SVG format**: Hero banner is pure SVG with embedded CSS animations
- **No build step**: Assets are used directly (no compilation required)
- **Read-only**: These are finalized assets - do not modify without explicit request
- **Embedding**: Use relative paths in markdown (`![Alt](assets/hero-banner.svg)`)

### Testing Requirements

- Verify SVG renders correctly in GitHub markdown
- Check animations work in modern browsers (Chrome, Firefox, Safari)
- Ensure accessibility attributes are present (alt text, semantic structure)
- Validate file size is reasonable (<20 KB for SVG)

### Common Patterns

- **Hero banner dimensions**: 1200×400 pixels (3:1 aspect ratio)
- **Color scheme**: Dark theme (#0f172a background) with blue-purple gradients (#3b82f6 → #8b5cf6)
- **Animations**: CSS keyframes for rotation, pulsing, flowing effects
- **Blueprint aesthetic**: Grid patterns, technical styling, systematic visual language

## Dependencies

### Internal

- Referenced by: `../README.md`, `../README.ko.md`

### External

None - pure SVG with embedded styles

<!-- MANUAL: -->
