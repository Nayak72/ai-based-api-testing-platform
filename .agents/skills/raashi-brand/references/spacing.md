# Raashi Cognitive Technologies — Spacing & Radius System

## 8-Point Spatial Grid

All paddings, margins, gaps, component dimensions, and layouts strictly adhere to an 8-point spatial grid.

| Scale Token | Pixel Value | Rem Value | Tailwind Class | Common Usage |
| :--- | :--- | :--- | :--- | :--- |
| `space-1` | `4px` | `0.25rem` | `p-1`, `gap-1` | Micro-padding, icon offsets |
| `space-2` | `8px` | `0.5rem` | `p-2`, `gap-2` | Button internal padding Y, compact gaps |
| `space-3` | `12px` | `0.75rem` | `p-3`, `gap-3` | Input padding Y, card compact padding |
| `space-4` | `16px` | `1rem` | `p-4`, `gap-4` | Card padding, standard grid gap |
| `space-6` | `24px` | `1.5rem` | `p-6`, `gap-6` | Section internal padding, container gaps |
| `space-8` | `32px` | `2rem` | `p-8`, `gap-8` | Modal padding, hero section gaps |
| `space-12` | `48px` | `3rem` | `py-12`, `gap-12` | Major section vertical padding |
| `space-16` | `64px` | `4rem` | `py-16` | Landing page section spacing |
| `space-24` | `96px` | `6rem` | `py-24` | Hero section top/bottom padding |

---

## Border Radius Standards

| Token | Radius Value | Tailwind Class | Applied Components |
| :--- | :--- | :--- | :--- |
| `radius-sm` | `8px` | `rounded-lg` | Input fields, buttons, dropdown menus, tooltips |
| `radius-md` | `12px` | `rounded-xl` | Standard cards, modal dialogs, select menus |
| `radius-lg` | `16px` | `rounded-2xl` | Large feature cards, dashboard widget containers |
| `radius-xl` | `24px` | `rounded-3xl` | Hero callout banners, pricing plan highlight cards |

---

## Elevation & Shadows

- **Card Soft Shadow**: `0 4px 20px -2px rgba(23, 40, 94, 0.06)`
- **Hover Soft Shadow**: `0 10px 30px -4px rgba(23, 40, 94, 0.12)`
- **Dropdown / Floating Shadow**: `0 20px 40px -8px rgba(23, 40, 94, 0.16)`
