# Raashi Cognitive Technologies — Color System

## Approved Brand Palette

Every single component, page, illustration, badge, border, and gradient MUST ONLY use the official brand colors listed below.

### Primary Swatches

| Name | Hex | RGB | Usage |
| :--- | :--- | :--- | :--- |
| **Primary Blue** | `#0560DF` | `5, 96, 223` | Main CTA buttons, active links, primary tabs, brand icons. |
| **Royal Blue** | `#0E2F9D` | `14, 47, 157` | Hover state for Primary Blue, focused borders, active sidebar items. |
| **Dark Navy** | `#17285E` | `23, 40, 94` | Primary body text, headings, dark mode cards/navigation, footer backgrounds. |
| **Orange** | `#F94F0E` | `249, 79, 14` | Secondary badges, notification pills, accent CTAs, key highlights. |
| **Red** | `#EE3128` | `238, 49, 40` | Danger buttons, error badges, destructive alerts, cognitive gradient end node. |
| **Magenta** | `#D11753` | `209, 23, 83` | Cognitive gradient middle node, AI active node indicators. |
| **White** | `#FFFFFF` | `255, 255, 255` | Card backgrounds, button text, crisp container fills. |
| **Surface** | `#F8FAFC` | `248, 250, 252` | Main page canvas background, input field backgrounds, table header fills. |

---

## Approved Gradients

### 1. Primary Cognitive Gradient
Used for hero text masks, primary feature cards, and AI processing nodes.
```css
background: linear-gradient(135deg, #0560DF 0%, #7A1FD0 50%, #EE3128 100%);
```

### 2. Secondary Motion Gradient
Used for active badges, secondary interactive highlights, and subtle border strokes.
```css
background: linear-gradient(135deg, #0560DF 0%, #F94F0E 100%);
```

---

## Strict Prohibitions

> [!CAUTION]
> - **Forbidden Colors**: Green, Yellow, Teal, Cyan, Lime, Amber, Pink, Purple outside the gradient node `#7A1FD0`.
> - **Forbidden Practices**:
>   - Do NOT use `#000000` pure black for text; use Dark Navy `#17285E` or muted navy variants.
>   - Do NOT use unapproved Tailwind default color utilities (e.g. `bg-emerald-500`, `text-indigo-600`).
>   - Do NOT use AI-invented pastel fills or random neon accents.
