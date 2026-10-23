# Raashi Cognitive Technologies — Motion & Animation System

## Motion Philosophy
Animations must feel snappy, subtle, and natural. Motion serves strictly to clarify state transitions, guide user focus, and enhance cognitive feedback.

> **Key Rule**: Duration MUST NOT exceed `300ms` for micro-interactions and `500ms` for page transitions.

---

## Technical Stack
- **Motion Engine**: Framer Motion (`motion/react`) or GSAP (`gsap`).
- **Easing**: Easing functions should emulate physical inertia (`cubic-bezier(0.16, 1, 0.3, 1)`).

---

## Standard Motion Variants (Framer Motion)

```tsx
import { motion } from "framer-motion";

// Standard Fade Up (For cards & list items)
export className FadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.3, ease: [0.16, 1, 0.3, 1] }
};

// Subtle Scale In (For modals, tooltips, popovers)
export const ScaleIn = {
  initial: { opacity: 0, scale: 0.96 },
  animate: { opacity: 1, scale: 1 },
  transition: { duration: 0.25, ease: [0.16, 1, 0.3, 1] }
};

// Staggered Container
export const StaggerContainer = {
  animate: {
    transition: {
      staggerChildren: 0.08
    }
  }
};
```

---

## Hover Motion Guidelines
- **Button Hover**: `whileHover={{ scale: 1.02 }}` & `whileTap={{ scale: 0.98 }}`.
- **Card Hover**: Subtle vertical lift `-4px` with smooth shadow transition.
- **Forbidden**: Excessive looping bounce, wild 3D spins, jarring full-screen slide shifts.
