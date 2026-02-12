<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-04 -->

# Assets Directory - Project Media and Resources

This directory contains static assets for the Synod project, including images, banners, and other media files used in documentation and marketing.

## Purpose

Centralized storage for project media assets that are referenced in README files, documentation, and other public-facing materials.

## Directory Structure

```
assets/
├── AGENTS.md           # This file
└── synod-banner.jpeg   # Project banner image for README
```

## Key Files

| File | Description |
|------|-------------|
| `synod-banner.jpeg` | Main project banner displayed in README.md |

## For AI Agents

### Working In This Directory

- **Do not modify images** without explicit user request
- **Reference assets** using relative paths from project root: `assets/synod-banner.jpeg`
- **New assets** should follow naming convention: `{purpose}-{variant}.{ext}`

### Asset Naming Conventions

| Pattern | Example | Use |
|---------|---------|-----|
| `{project}-banner.{ext}` | `synod-banner.jpeg` | README header images |
| `{feature}-screenshot.{ext}` | `debate-screenshot.png` | Feature demonstrations |
| `{diagram}-flow.{ext}` | `architecture-flow.svg` | Technical diagrams |
| `icon-{size}.{ext}` | `icon-128.png` | Icons at various sizes |

### Supported Formats

| Format | Use Case |
|--------|----------|
| `.jpeg/.jpg` | Photos, banners with gradients |
| `.png` | Screenshots, diagrams with transparency |
| `.svg` | Vector graphics, logos, icons |
| `.gif` | Animated demonstrations |

### Image Optimization

Before adding new images:
1. Compress images to reduce file size
2. Use appropriate format for content type
3. Keep banner images under 500KB
4. Use descriptive filenames

## Dependencies

### Referenced By
- `README.md` - Main project README
- `README.ko.md` - Korean README

---

**Last Updated**: 2026-02-04
**Assets Count**: 1 (synod-banner.jpeg)
