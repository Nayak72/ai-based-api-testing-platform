# Raashi Cognitive Technologies — Do's and Don'ts

## Summary Checklist

### DO'S
- **DO** use `#0560DF` (Primary Blue) for main action buttons, primary links, and active controls.
- **DO** use `#17285E` (Dark Navy) for body copy, headers, dark surfaces, and navigation elements.
- **DO** use `#F8FAFC` (Surface) as the main page canvas background.
- **DO** use the exact 8-point spatial grid for all margins, paddings, and gaps.
- **DO** use standard border radii: `8px`, `12px`, `16px`, `24px`.
- **DO** use Lucide icons with consistent 1.75px stroke width.
- **DO** use `shadcn/ui` component primitives for all interactive elements.
- **DO** ensure WCAG AA contrast compliance across all text and interactive focus states.

---

### DON'TS
- **DON'T** introduce Green, Yellow, Teal, Cyan, Lime, or random unapproved colors under ANY circumstance.
- **DON'T** use default Tailwind colors (`bg-blue-500`, `text-indigo-600`, `bg-purple-500`) unless mapped to brand tokens.
- **DON'T** use generic AI purple/glow aesthetic blobs outside the approved Primary Gradient (`#0560DF` → `#7A1FD0` → `#EE3128`).
- **DON'T** use serif or decorative display fonts.
- **DON'T** build custom buttons or cards when `shadcn/ui` primitives are available.
- **DON'T** use multi-color or 3D icons.
- **DON'T** create dark borders (`border-black` or `border-gray-900`); use soft borders `border-[#17285E]/10`.
