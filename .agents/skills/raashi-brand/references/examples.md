# Raashi Cognitive Technologies — Implementation Reference Examples

## Example 1: Brand Hero Component (React + Tailwind + Lucide + Motion)

```tsx
import React from 'react';
import { motion } from 'framer-motion';
import { BrainCircuit, ArrowRight, Sparkles, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export function RaashiHero() {
  return (
    <section className="relative overflow-hidden bg-[#F8FAFC] py-20 lg:py-28">
      {/* Subtle Radial Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-[#0560DF]/5 blur-[120px] rounded-full pointer-events-none" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10 max-w-6xl">
        <div className="text-center max-w-3xl mx-auto space-y-6">
          
          {/* Brand Badge */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#0560DF]/10 border border-[#0560DF]/20 text-[#0560DF] text-xs font-semibold uppercase tracking-wider"
          >
            <Sparkles className="w-3.5 h-3.5" />
            Raashi Cognitive Architecture v2.0
          </motion.div>

          {/* Display Heading with Brand Gradient */}
          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.1 }}
            className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-[#17285E] leading-[1.1]"
          >
            Transforming Knowledge into{' '}
            <span className="bg-gradient-to-r from-[#0560DF] via-[#7A1FD0] to-[#EE3128] bg-clip-text text-transparent">
              Intelligent Solutions
            </span>
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.2 }}
            className="text-lg sm:text-xl text-[#17285E]/80 font-normal leading-relaxed"
          >
            Empower your enterprise with autonomous cognitive synthesis, structured knowledge graphs, and real-time decision intelligence.
          </motion.p>

          {/* Dual CTAs */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.3 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2"
          >
            <Button size="lg" className="bg-[#0560DF] hover:bg-[#0E2F9D] text-white rounded-xl px-8 h-12 text-base font-semibold shadow-md gap-2 w-full sm:w-auto">
              Deploy Platform <ArrowRight className="w-5 h-5" />
            </Button>

            <Button variant="outline" size="lg" className="border-[#17285E]/20 text-[#17285E] hover:bg-white bg-white/80 rounded-xl px-8 h-12 text-base font-semibold w-full sm:w-auto">
              Schedule Architecture Audit
            </Button>
          </motion.div>

          {/* Trust Badges */}
          <div className="flex items-center justify-center gap-6 pt-8 text-xs text-[#17285E]/60 font-medium">
            <span className="flex items-center gap-1.5"><ShieldCheck className="w-4 h-4 text-[#0560DF]" /> SOC2 Type II Certified</span>
            <span className="flex items-center gap-1.5"><BrainCircuit className="w-4 h-4 text-[#F94F0E]" /> Cognitive Graph Engine</span>
          </div>

        </div>
      </div>
    </section>
  );
}
```
