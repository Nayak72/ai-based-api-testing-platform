# Raashi Cognitive Technologies — Enterprise UI Patterns

## Architectural Archetypes & Page Layouts

### 1. Landing Page Pattern
- **Hero Section**: Clean surface background (`#F8FAFC`), optional subtle cognitive radial glow (`rgba(5, 96, 223, 0.05)`), brand gradient display text (`#0560DF` → `#7A1FD0` → `#EE3128`), dual CTAs (Primary Blue CTA + Secondary White border CTA), hero interactive cognitive preview container with 24px radius.
- **Trust Banner**: Monochrome enterprise logos in muted Dark Navy (`#17285E`/40 opacity).
- **Feature Matrix**: 3-column or 2-column grid using 16px radius White cards, Lucide icon badges in `#F8FAFC` rounded boxes, 24px internal padding.
- **Cognitive Process Section**: Interactive tabbed or stepped workflow display demonstrating knowledge transformation.
- **CTA Footer Section**: Dark Navy (`#17285E`) background container with white text and Primary Blue / Orange accent buttons.

---

### 2. Enterprise SaaS Dashboard Pattern
- **Header Nav**: Fixed top bar in `#FFFFFF`, bottom border `1px solid rgba(23, 40, 94, 0.08)`, search bar, notifications, workspace switcher.
- **Sidebar**: Dark Navy (`#17285E`) or Surface (`#F8FAFC`) sidebar with 8px radius active navigation items styled in Primary Blue (`#0560DF`).
- **Metric Cards Grid**: 4-column KPI metric cards with big display numbers in Dark Navy, growth indicators in Orange (`#F94F0E`) or Primary Blue.
- **Data Table**: Surface (`#F8FAFC`) header row, 14px text, hover highlight in `#F8FAFC`, clean pagination controls.

---

### 3. Glassmorphism Guidance
- Glassmorphism is allowed **ONLY** for floating sticky headers, dropdown menus, overlay modals, and command palettes.
- Specification: `background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(12px); border: 1px solid rgba(23, 40, 94, 0.08);`.
