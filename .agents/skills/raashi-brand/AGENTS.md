# AGENTS.md — Raashi Cognitive Technologies Execution Rules

When generating code or UI designs under the Raashi Cognitive Technologies scope:

1. **Strict Brand Compliance**:
   - Check `.agents/skills/raashi-brand/tokens/colors.json` before writing color utilities.
   - Use Tailwind theme variables specified in `.agents/skills/raashi-brand/tailwind/tailwind.config.ts`.
   - Never output generic AI styling patterns like purple glow background blobs, neon green accents, or generic material design cards.

2. **Component Reuse**:
   - Always map UI elements to Shadcn UI primitives configured in `.agents/skills/raashi-brand/shadcn/theme.css`.
   - Use Lucide icons only.

3. **Pre-flight Brand Checklist**:
   - [ ] Primary Blue (`#0560DF`) used for main CTAs and active states.
   - [ ] Dark Navy (`#17285E`) used for headings and high-contrast body text.
   - [ ] Surface (`#F8FAFC`) used for layout canvas background.
   - [ ] No unauthorized colors (No green, yellow, teal, custom pinks/purples).
   - [ ] Radii set to 8px, 12px, 16px, or 24px.
   - [ ] Motion powered by Framer Motion / Motion.dev with duration <= 0.3s.
