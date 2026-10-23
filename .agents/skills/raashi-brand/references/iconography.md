# Raashi Cognitive Technologies — Iconography Standard

## Library Specification
- **Exclusive Library**: `lucide-react`.
- **Stroke Width**: `1.75px` default (or `1.5px` for smaller 16px icons; `2px` for bold actions).
- **Color Mapping**: Monochrome only, mapped to `#17285E` (Dark Navy), `#0560DF` (Primary Blue), `#F94F0E` (Orange), or `#FFFFFF` (On dark background).

> [!CAUTION]
> **NO Colorful / Multi-hue Icons**. Do NOT use FontAwesome multi-color icons, 3D illustrations, or emojis as functional UI icons.

---

## Icon Sizing Standards

| Token | Size | Stroke | Common Lucide Icons Used |
| :--- | :--- | :--- | :--- |
| `icon-sm` | `16px` (`w-4 h-4`) | `1.5px` | `ChevronDown`, `Check`, `X`, `ArrowRight`, `Search` |
| `icon-md` | `20px` (`w-5 h-5`) | `1.75px` | `BrainCircuit`, `Sparkles`, `Cpu`, `Database`, `Shield` |
| `icon-lg` | `24px` (`w-6 h-6`) | `2.0px` | `Layers`, `Network`, `Activity`, `Terminal`, `Sliders` |
| `icon-xl` | `32px` (`w-8 h-8`) | `2.0px` | Feature card header icons enclosed in `#F8FAFC` circular/rounded containers |

---

## Code Example

```tsx
import { BrainCircuit, ArrowRight } from "lucide-react";

export function FeatureIcon({ icon: Icon = BrainCircuit }) {
  return (
    <div className="w-12 h-12 rounded-xl bg-[#F8FAFC] border border-[#17285E]/10 flex items-center justify-center text-[#0560DF]">
      <Icon className="w-6 h-6 stroke-[1.75]" />
    </div>
  );
}
```
