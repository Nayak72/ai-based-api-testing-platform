---
name: raashi-brand
description: Official Brand Identity & Design System Skill Pack for Raashi Cognitive Technologies Pvt. Ltd. ("Transforming Knowledge into Intelligent Solutions"). Enforces strict brand identity, exact color palette, custom gradients, typography, spacing, component patterns, Tailwind/shadcn configuration, and UI guidelines across all AI-generated interfaces.
---

# Raashi Cognitive Technologies — Official Brand Skill Pack

> **Tagline:** Transforming Knowledge into Intelligent Solutions
> **Company:** Raashi Cognitive Technologies Pvt. Ltd.

This skill pack governs every AI-generated UI, landing page, SaaS application, dashboard, admin panel, mobile interface, marketing site, and documentation layout produced for Raashi Cognitive Technologies.

---

## 1. BRAND IDENTITY & CORE VALUES

Raashi Cognitive Technologies creates enterprise-grade cognitive AI platforms that synthesize knowledge into actionable intelligence. Interfaces generated under this brand must convey:
- **Cognitive Precision**: Clean, purposeful, structured visual layout.
- **Enterprise Trust**: Deep navy anchor, crisp royal blue controls, high readability.
- **Dynamic Innovation**: Vivid blue-to-magenta-to-red gradients reserved for hero highlights and key cognitive nodes.

---

## 2. OFFICIAL PALETTE & STRICT COLOR RULES

### Approved Colors ONLY

| Role | Color Name | Hex Code | HSL Equivalent | Tailwind Token |
| :--- | :--- | :--- | :--- | :--- |
| **Primary Accent** | Primary Blue | `#0560DF` | `hsl(215, 96%, 45%)` | `brand-blue` |
| **Hover / Deep Action** | Royal Blue | `#0E2F9D` | `hsl(226, 84%, 34%)` | `brand-royal` |
| **Primary Text & Dark Surface**| Dark Navy | `#17285E` | `hsl(226, 61%, 23%)` | `brand-navy` |
| **Secondary Accent / Highlight**| Orange | `#F94F0E` | `hsl(16, 95%, 52%)` | `brand-orange` |
| **Error / Alert / Danger** | Red | `#EE3128` | `hsl(2, 84%, 54%)` | `brand-red` |
| **Cognitive Gradient Node** | Magenta | `#D11753` | `hsl(341, 80%, 46%)` | `brand-magenta` |
| **Card / Canvas White** | White | `#FFFFFF` | `hsl(0, 0%, 100%)` | `white` |
| **Background / Muted Surface** | Surface | `#F8FAFC` | `hsl(210, 40%, 98%)` | `brand-surface` |

> [!CAUTION]
> **STRICT COLOR RESTRICTIONS**
> - **NEVER** use Green, Yellow, Teal, Cyan, Random Pink, Random Purple, or arbitrary AI-generated colors.
> - **NEVER** use default Tailwind colors (`blue-500`, `purple-600`, `emerald-500`, `amber-400`, `indigo-600`, etc.) without mapping to brand tokens.
> - **NEVER** invent unsanctioned background tinting or decorative badges outside the brand palette.

### Approved Gradients ONLY

1. **Primary Cognitive Gradient** (Hero text, main feature highlights, primary AI nodes):
   `linear-gradient(135deg, #0560DF 0%, #7A1FD0 50%, #EE3128 100%)`
2. **Secondary Motion Gradient** (Subtle badges, accent borders, interactive hover states):
   `linear-gradient(135deg, #0560DF 0%, #F94F0E 100%)`

---

## 3. TYPOGRAPHY & SPACING SYSTEM

- **Primary Font**: `Inter`, `Plus Jakarta Sans`, or `Manrope` (sans-serif only; no decorative/serif fonts).
- **Grid Baseline**: Strict 8-point spatial grid (`8px`, `16px`, `24px`, `32px`, `48px`, `64px`, `96px`).
- **Border Radius**:
  - `sm`: `8px` (`rounded-lg`)
  - `md`: `12px` (`rounded-xl`)
  - `lg`: `16px` (`rounded-2xl`)
  - `xl`: `24px` (`rounded-3xl`)

---

## 4. SHADCN / UI & COMPONENT RULES

- **Always** build interfaces using `shadcn/ui` primitives styled with Raashi CSS variable mappings.
- **Buttons**:
  - Primary: `#0560DF` background, white text. Hover: `#0E2F9D`.
  - Secondary: `#FFFFFF` background, `#17285E` border, `#17285E` text.
  - Accent: `#F94F0E` background, white text.
  - Danger: `#EE3128` background, white text.
- **Cards**: White background (`#FFFFFF`), subtle shadow (`0 4px 20px -2px rgba(23, 40, 94, 0.06)`), 12px/16px rounded corners, no heavy black borders.
- **Icons**: Lucide React icons exclusively, fixed 1.5px or 2px stroke, monochrome mapped to brand navy/blue.

---

## 5. QUICK REFERENCE DIRECTORY

Detailed sub-documents are available in the `./references` directory:
- [Brand Guidelines](file://./references/brand-guidelines.md)
- [Colors Specification](file://./references/colors.md)
- [Typography System](file://./references/typography.md)
- [Spacing & Radius](file://./references/spacing.md)
- [Animations & Motion](file://./references/animations.md)
- [Iconography Standard](file://./references/iconography.md)
- [Accessibility Rules](file://./references/accessibility.md)
- [UI Patterns](file://./references/ui-patterns.md)
- [Component Specifications](file://./references/components.md)
- [Prompt Library](file://./references/prompts.md)
- [Do's and Don'ts](file://./references/dos-and-donts.md)
- [Implementation Examples](file://./references/examples.md)
