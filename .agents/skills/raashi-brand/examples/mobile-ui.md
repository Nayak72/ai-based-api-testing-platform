# Raashi Cognitive Technologies — Mobile UI Blueprint

```tsx
import React from 'react';
import { BrainCircuit, Sparkles, Send, Mic, Menu, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function RaashiMobileUI() {
  return (
    <div className="max-w-sm mx-auto h-[700px] bg-[#F8FAFC] rounded-[32px] border-4 border-[#17285E]/20 shadow-2xl flex flex-col overflow-hidden text-[#17285E]">
      {/* Top Mobile Bar */}
      <header className="h-14 bg-white border-b border-[#17285E]/8 px-4 flex items-center justify-between">
        <Menu className="w-5 h-5 text-[#17285E]" />
        <span className="font-bold text-sm text-[#17285E]">Raashi Mobile Cognitive</span>
        <div className="w-7 h-7 rounded-full bg-[#0560DF] text-white flex items-center justify-center text-xs font-bold">R</div>
      </header>

      {/* Main Conversation Stream */}
      <div className="flex-1 p-4 space-y-4 overflow-y-auto">
        <div className="bg-white p-4 rounded-2xl border border-[#17285E]/8 shadow-sm space-y-2">
          <div className="flex items-center gap-2 text-xs font-semibold text-[#0560DF]">
            <Sparkles className="w-3.5 h-3.5" /> Cognitive Synthesis
          </div>
          <p className="text-xs text-[#17285E] leading-relaxed">
            Ingested 4,200 enterprise quarterly filings. Knowledge graph ready for natural query synthesis.
          </p>
        </div>
      </div>

      {/* Mobile Input Field */}
      <div className="p-3 bg-white border-t border-[#17285E]/8 flex items-center gap-2">
        <input 
          type="text" 
          placeholder="Ask Raashi Cognitive..." 
          className="flex-1 text-xs bg-[#F8FAFC] border border-[#17285E]/10 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[#0560DF]"
        />
        <Button size="icon" className="w-8 h-8 rounded-xl bg-[#0560DF] text-white hover:bg-[#0E2F9D]">
          <Send className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}
```
