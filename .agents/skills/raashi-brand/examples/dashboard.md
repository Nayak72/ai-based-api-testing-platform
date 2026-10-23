# Raashi Cognitive Technologies — SaaS Dashboard Blueprint

```tsx
import React from 'react';
import { LayoutDashboard, BrainCircuit, Database, Activity, Search, Bell, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

export default function RaashiDashboard() {
  return (
    <div className="flex h-screen bg-[#F8FAFC] text-[#17285E] font-sans">
      {/* Sidebar */}
      <aside className="w-64 bg-[#17285E] text-white flex flex-col">
        <div className="h-16 px-6 flex items-center gap-3 border-b border-white/10">
          <div className="w-8 h-8 rounded-lg bg-[#0560DF] flex items-center justify-center font-bold">R</div>
          <span className="font-bold text-base tracking-tight">Raashi OS</span>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          <a href="#" className="flex items-center gap-3 px-3 py-2 rounded-lg bg-[#0560DF] text-white font-medium text-sm">
            <LayoutDashboard className="w-4 h-4" /> Overview
          </a>
          <a href="#" className="flex items-center gap-3 px-3 py-2 rounded-lg text-white/80 hover:bg-white/5 font-medium text-sm">
            <BrainCircuit className="w-4 h-4" /> Cognitive Nodes
          </a>
          <a href="#" className="flex items-center gap-3 px-3 py-2 rounded-lg text-white/80 hover:bg-white/5 font-medium text-sm">
            <Database className="w-4 h-4" /> Knowledge Base
          </a>
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-y-auto">
        {/* Top Header */}
        <header className="h-16 bg-white border-b border-[#17285E]/8 px-8 flex items-center justify-between">
          <h1 className="text-xl font-bold text-[#17285E]">Cognitive Intelligence Overview</h1>
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" className="text-[#17285E]"><Bell className="w-5 h-5" /></Button>
            <div className="w-9 h-9 rounded-full bg-[#0560DF]/10 border border-[#0560DF]/30 flex items-center justify-center text-[#0560DF] font-bold text-sm">
              RC
            </div>
          </div>
        </header>

        {/* Dashboard Grid */}
        <div className="p-8 space-y-8">
          <div className="grid md:grid-cols-4 gap-6">
            <Card className="bg-white border-[#17285E]/8 rounded-xl">
              <CardHeader className="pb-2">
                <span className="text-xs font-semibold text-[#17285E]/60 uppercase">Knowledge Vector Graph</span>
                <CardTitle className="text-3xl font-bold text-[#17285E]">1.42M</CardTitle>
              </CardHeader>
            </Card>

            <Card className="bg-white border-[#17285E]/8 rounded-xl">
              <CardHeader className="pb-2">
                <span className="text-xs font-semibold text-[#17285E]/60 uppercase">Autonomous Agent Calls</span>
                <CardTitle className="text-3xl font-bold text-[#0560DF]">894.2K</CardTitle>
              </CardHeader>
            </Card>

            <Card className="bg-white border-[#17285E]/8 rounded-xl">
              <CardHeader className="pb-2">
                <span className="text-xs font-semibold text-[#17285E]/60 uppercase">Cognitive Precision</span>
                <CardTitle className="text-3xl font-bold text-[#F94F0E]">99.84%</CardTitle>
              </CardHeader>
            </Card>

            <Card className="bg-white border-[#17285E]/8 rounded-xl">
              <CardHeader className="pb-2">
                <span className="text-xs font-semibold text-[#17285E]/60 uppercase">Active Pipelines</span>
                <CardTitle className="text-3xl font-bold text-[#17285E]">128</CardTitle>
              </CardHeader>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}
```
