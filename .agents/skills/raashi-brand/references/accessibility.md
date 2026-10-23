# Raashi Cognitive Technologies — Accessibility Standards (WCAG 2.1 AA)

## Accessibility Rules

Every UI created under the Raashi Cognitive Technologies brand must comply with **WCAG 2.1 Level AA**.

### 1. Contrast Ratios
- **Normal Text**: Contrast ratio of at least `4.5:1` against background.
  - Dark Navy (`#17285E`) on Surface (`#F8FAFC`): **11.2:1** (PASS AAA)
  - Dark Navy (`#17285E`) on White (`#FFFFFF`): **12.1:1** (PASS AAA)
  - Primary Blue (`#0560DF`) on White (`#FFFFFF`): **4.7:1** (PASS AA)
  - White (`#FFFFFF`) on Primary Blue (`#0560DF`): **4.7:1** (PASS AA)
- **Large Text (24px+ or 18px+ Bold)**: Contrast ratio of at least `3.0:1`.

---

### 2. Focus States
- All interactive controls (buttons, links, inputs, tabs, switches) MUST have a prominent, visible focus ring.
- **Focus Ring Style**: `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0560DF] focus-visible:ring-offset-2`.

---

### 3. Keyboard Navigation
- All modals must trap focus and close on `Escape`.
- Dropdowns, select boxes, and tabs must respond to `Arrow` keys, `Enter`, and `Space`.
- Navigation bars must support `Tab` cycling without focus loss.

---

### 4. Semantic Markup & ARIA
- Use HTML5 landmark elements: `<header>`, `<nav>`, `<main>`, `<aside>`, `<footer>`.
- Interactive icon-only buttons MUST include `aria-label`.
- Dynamic status panels must use `aria-live="polite"`.
