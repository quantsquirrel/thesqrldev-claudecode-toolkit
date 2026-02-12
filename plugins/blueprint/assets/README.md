# Blueprint Helix Assets

## Hero Banner

### Overview

The Hero banner (`hero-banner.svg`) is a professional, animated SVG graphic that represents the core concepts of Blueprint Helix:

- **PDCA Cycle** (left): Rotating circular diagram showing Plan-Do-Check-Act iterative improvement
- **Blueprint Grid**: Background pattern representing systematic planning
- **Pipeline Flow** (right): Animated stages representing the development pipeline
- **Feature Pills** (bottom): PDCA, Gap Analysis, and Pipeline capabilities

### Specifications

- **Format**: SVG (Scalable Vector Graphics)
- **Dimensions**: 1200 × 400 pixels
- **File Size**: ~9 KB
- **Features**:
  - Fully responsive and scalable
  - CSS animations (PDCA rotation, pipeline flow)
  - Dark theme with blue-purple gradient accents
  - Blueprint-style grid pattern background

### Usage

#### In README (Markdown)

```markdown
![Blueprint Helix Hero Banner](assets/hero-banner.svg)
```

#### In HTML

```html
<img src="assets/hero-banner.svg" alt="Blueprint Helix - Systematic Development" width="100%">
```

#### Direct Link

```
https://raw.githubusercontent.com/quantsquirrel/claude-blueprint-helix/main/assets/hero-banner.svg
```

### Design Elements

| Element | Color | Purpose |
|---------|-------|---------|
| Background | `#0f172a` → `#1e293b` | Dark slate gradient |
| PDCA Segments | Blue, Purple, Cyan, Green | Cycle visualization |
| Title Gradient | `#3b82f6` → `#8b5cf6` | Blue to purple accent |
| Grid Pattern | `#1e3a8a` (30% opacity) | Blueprint aesthetic |
| Feature Pills | Color-coded borders | Capability highlights |

### Animations

- **PDCA Cycle**: 20-second continuous rotation
- **PDCA Segments**: 4-second pulsing opacity (sequential)
- **Pipeline Stages**: 2-second height animation (staggered)
- **Pipeline Arrow**: Continuous dash animation
- **Decorative Dots**: 3-4 second opacity fade

### Accessibility

- Alt text: "Blueprint Helix - Systematic Development Through Iterative Improvement"
- Semantic SVG structure with proper labels
- High contrast ratios for readability
- Animation respects `prefers-reduced-motion` (browser default)

### License

MIT License - Same as Blueprint Helix project

---

**Created**: 2026-02-12
**Version**: 1.0.0
**Maintained by**: Blueprint Helix Team
