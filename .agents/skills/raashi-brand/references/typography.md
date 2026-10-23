# Raashi Cognitive Technologies — Typography System

## Typography Principles
- **Modern, Professional, Minimal, Readable**.
- Allowed Families: **Inter**, **Plus Jakarta Sans**, or **Manrope**.
- Strictly NO serif or decorative display fonts (e.g. Playfair, Comic Sans, Papyrus, Pacifico).

---

## Type Hierarchy & Utility Classes

| Role | Font Family | Size | Weight | Tracking | Line Height | Usage |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Hero Display** | Inter / Plus Jakarta Sans | `48px` - `64px` | Bold (`700`) | `-0.03em` | `1.1` | Main page hero titles |
| **Heading 1** | Inter / Plus Jakarta Sans | `36px` - `40px` | Bold (`700`) | `-0.02em` | `1.2` | Major section headers |
| **Heading 2** | Inter / Plus Jakarta Sans | `28px` - `32px` | SemiBold (`600`) | `-0.01em` | `1.25` | Card group titles, modal headers |
| **Heading 3** | Inter / Manrope | `20px` - `24px` | SemiBold (`600`) | `0` | `1.3` | Card headers, table section titles |
| **Body Large** | Inter / Manrope | `18px` | Regular / Medium | `0` | `1.5` | Subtitles, hero intro paragraphs |
| **Body Base** | Inter / Manrope | `16px` | Regular (`400`) | `0` | `1.5` | Standard body text, form labels |
| **Body Small** | Inter / Manrope | `14px` | Regular / Medium | `0` | `1.4` | Table cell data, card metadata |
| **Caption** | Inter / Manrope | `12px` | Medium (`500`) | `0.02em` | `1.3` | Micro-badges, timestamp labels |

---

## Code Example (Tailwind)

```tsx
export function HeroHeading({ children }: { children: React.ReactNode }) {
  return (
    <h1 className="font-sans text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-[#17285E] leading-[1.1]">
      {children}
    </h1>
  );
}

export function GradientText({ children }: { children: React.ReactNode }) {
  return (
    <span className="bg-gradient-to-r from-[#0560DF] via-[#7A1FD0] to-[#EE3128] bg-clip-text text-transparent">
      {children}
    </span>
  );
}
```
