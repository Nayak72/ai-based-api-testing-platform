# Raashi Cognitive Technologies — Component Specifications

## Component Rules & Variants

### 1. Button Component (`shadcn/ui Button`)

```tsx
import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0560DF] focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98]",
  {
    variants: {
      variant: {
        default: "bg-[#0560DF] text-white hover:bg-[#0E2F9D] shadow-sm",
        secondary: "bg-white text-[#17285E] border border-[#17285E]/20 hover:bg-[#F8FAFC]",
        accent: "bg-[#F94F0E] text-white hover:bg-[#F94F0E]/90 shadow-sm",
        danger: "bg-[#EE3128] text-white hover:bg-[#EE3128]/90 shadow-sm",
        outline: "border border-[#0560DF] text-[#0560DF] bg-transparent hover:bg-[#0560DF]/5",
        ghost: "text-[#17285E] hover:bg-[#F8FAFC] hover:text-[#0560DF]",
        link: "text-[#0560DF] underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 rounded-lg px-3 text-xs",
        lg: "h-12 rounded-xl px-6 text-base font-semibold",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)
```

---

### 2. Card Component (`shadcn/ui Card`)
- **Background**: `#FFFFFF`
- **Border**: `1px solid rgba(23, 40, 94, 0.08)`
- **Shadow**: `0 4px 20px -2px rgba(23, 40, 94, 0.06)`
- **Radius**: `12px` (standard) or `16px` (featured)

---

### 3. Badge Component
- **Primary Pill**: `bg-[#0560DF]/10 text-[#0560DF] border border-[#0560DF]/20`
- **Orange Highlight Pill**: `bg-[#F94F0E]/10 text-[#F94F0E] border border-[#F94F0E]/20`
- **Dark Navy Pill**: `bg-[#17285E] text-white`
- **Gradient Pill**: `bg-gradient-to-r from-[#0560DF] via-[#7A1FD0] to-[#EE3128] text-white`
