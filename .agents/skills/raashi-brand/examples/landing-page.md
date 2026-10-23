# Raashi Cognitive Technologies — Landing Page Example Blueprint

## Overview
Enterprise SaaS Landing Page adhering strictly to Raashi Cognitive Technologies brand identity.

- **Hero Headline**: "Transforming Knowledge into Intelligent Solutions"
- **Primary CTA**: "Deploy Platform" (`#0560DF`)
- **Secondary CTA**: "Schedule Architecture Audit" (`#FFFFFF` with `#17285E` stroke)
- **Palette**: `#0560DF`, `#0E2F9D`, `#17285E`, `#F94F0E`, `#EE3128`, `#D11753`, `#FFFFFF`, `#F8FAFC`.

---

## Code Blueprint (React + Tailwind + Lucide + Motion)

```tsx
import React from 'react';
import { motion } from 'framer-motion';
import { BrainCircuit, ArrowRight, ShieldCheck, Database, Sparkles, Layers, Cpu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';

export default function RaashiLandingPage() {
  return (
    <div className="min-h-screen bg-[#F8FAFC] text-[#17285E] font-sans antialiased">
      {/* Sticky Header */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-[#17285E]/8">
        <div className="container mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-lg bg-[#0560DF] text-white flex items-center justify-center font-bold text-lg">
              R
            </div>
            <span className="font-bold text-lg text-[#17285E] tracking-tight">Raashi Cognitive</span>
          </div>
          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-[#17285E]/80">
            <a href="#platform" className="hover:text-[#0560DF]">Platform</a>
            <a href="#architecture" className="hover:text-[#0560DF]">Architecture</a>
            <a href="#solutions" className="hover:text-[#0560DF]">Solutions</a>
            <a href="#enterprise" className="hover:text-[#0560DF]">Enterprise</a>
          </nav>
          <div className="flex items-center gap-4">
            <Button variant="ghost" className="text-[#17285E] hover:text-[#0560DF]">Sign In</Button>
            <Button className="bg-[#0560DF] hover:bg-[#0E2F9D] text-white rounded-lg">Get Started</Button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-24 text-center relative overflow-hidden">
        <div className="container mx-auto px-6 max-w-4xl space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#0560DF]/10 border border-[#0560DF]/20 text-[#0560DF] text-xs font-semibold uppercase">
            <Sparkles className="w-3.5 h-3.5 text-[#F94F0E]" />
            Cognitive Enterprise Platform
          </div>
          <h1 className="text-5xl md:text-6xl font-bold tracking-tight text-[#17285E]">
            Transforming Knowledge into{' '}
            <span className="bg-gradient-to-r from-[#0560DF] via-[#7A1FD0] to-[#EE3128] bg-clip-text text-transparent">
              Intelligent Solutions
            </span>
          </h1>
          <p className="text-xl text-[#17285E]/80 leading-relaxed max-w-2xl mx-auto">
            Synthesize unstructured enterprise data into real-time autonomous reasoning graphs and executive intelligence pipelines.
          </p>
          <div className="flex items-center justify-center gap-4 pt-4">
            <Button size="lg" className="bg-[#0560DF] hover:bg-[#0E2F9D] text-white rounded-xl px-8 h-12 text-base font-semibold shadow-md gap-2">
              Deploy Platform <ArrowRight className="w-5 h-5" />
            </Button>
            <Button variant="outline" size="lg" className="border-[#17285E]/20 text-[#17285E] bg-white rounded-xl px-8 h-12 text-base font-semibold">
              Explore Architecture
            </Button>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20 bg-white border-y border-[#17285E]/8">
        <div className="container mx-auto px-6 max-w-6xl">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-3xl font-bold text-[#17285E]">Enterprise Cognitive Architecture</h2>
            <p className="text-[#17285E]/70 mt-2">Built for high-scale enterprise knowledge ingestion and neural search.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            <Card className="rounded-2xl border-[#17285E]/8 shadow-sm hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="w-12 h-12 rounded-xl bg-[#F8FAFC] flex items-center justify-center text-[#0560DF] mb-4">
                  <BrainCircuit className="w-6 h-6" />
                </div>
                <CardTitle className="text-xl font-bold text-[#17285E]">Knowledge Graph AI</CardTitle>
                <CardDescription className="text-[#17285E]/70">Contextual graph neural mapping across unstructured enterprise repositories.</CardDescription>
              </CardHeader>
            </Card>

            <Card className="rounded-2xl border-[#17285E]/8 shadow-sm hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="w-12 h-12 rounded-xl bg-[#F8FAFC] flex items-center justify-center text-[#F94F0E] mb-4">
                  <Cpu className="w-6 h-6" />
                </div>
                <CardTitle className="text-xl font-bold text-[#17285E]">Autonomous Reasoning</CardTitle>
                <CardDescription className="text-[#17285E]/70">Multi-agent cognitive engines resolving complex multi-step workflows.</CardDescription>
              </CardHeader>
            </Card>

            <Card className="rounded-2xl border-[#17285E]/8 shadow-sm hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="w-12 h-12 rounded-xl bg-[#F8FAFC] flex items-center justify-center text-[#0560DF] mb-4">
                  <Database className="w-6 h-6" />
                </div>
                <CardTitle className="text-xl font-bold text-[#17285E]">Vector Synthesis</CardTitle>
                <CardDescription className="text-[#17285E]/70">Sub-millisecond semantic search across petabyte-scale knowledge bases.</CardDescription>
              </CardHeader>
            </Card>
          </div>
        </div>
      </section>
    </div>
  );
}
```
