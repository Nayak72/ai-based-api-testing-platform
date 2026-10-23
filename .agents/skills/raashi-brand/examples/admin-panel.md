# Raashi Cognitive Technologies — Admin Panel Blueprint

```tsx
import React from 'react';
import { Shield, Key, Users, Settings, Plus, Search, CheckCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

export default function RaashiAdminPanel() {
  return (
    <div className="p-8 bg-[#F8FAFC] min-h-screen text-[#17285E] font-sans">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-[#17285E]">Enterprise Security & API Governance</h1>
            <p className="text-sm text-[#17285E]/70">Manage cognitive pipeline access keys and IAM policy roles.</p>
          </div>
          <Button className="bg-[#0560DF] hover:bg-[#0E2F9D] text-white rounded-lg gap-2">
            <Plus className="w-4 h-4" /> Provision Cognitive Key
          </Button>
        </div>

        <div className="bg-white rounded-xl border border-[#17285E]/8 shadow-sm overflow-hidden">
          <Table>
            <TableHeader className="bg-[#F8FAFC]">
              <TableRow>
                <TableHead className="text-[#17285E] font-semibold">Key Identifier</TableHead>
                <TableHead className="text-[#17285E] font-semibold">Scope</TableHead>
                <TableHead className="text-[#17285E] font-semibold">Status</TableHead>
                <TableHead className="text-[#17285E] font-semibold">Last Active</TableHead>
                <TableHead className="text-right text-[#17285E] font-semibold">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell className="font-mono text-xs text-[#17285E]">rct_live_89a7f...d92</TableCell>
                <TableCell className="text-sm text-[#17285E]">Read/Write Cognitive Knowledge Graph</TableCell>
                <TableCell>
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#0560DF]/10 text-[#0560DF]">
                    <CheckCircle className="w-3 h-3" /> Active
                  </span>
                </TableCell>
                <TableCell className="text-sm text-[#17285E]/70">2 mins ago</TableCell>
                <TableCell className="text-right">
                  <Button variant="ghost" size="sm" className="text-[#EE3128] hover:bg-[#EE3128]/5">Revoke</Button>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}
```
