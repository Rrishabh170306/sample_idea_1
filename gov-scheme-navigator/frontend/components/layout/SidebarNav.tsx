"use client";

import { FileText, LayoutDashboard, MessageSquare, ShieldCheck, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

const items = [
  { label: 'Workspace', icon: LayoutDashboard },
  { label: 'Chat', icon: MessageSquare },
  { label: 'Eligibility', icon: ShieldCheck },
  { label: 'Artifacts', icon: FileText },
];

export function SidebarNav({ collapsed = false }: { collapsed?: boolean }) {
  return (
    <div className="flex h-full flex-col gap-4">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-sky-500/15 text-sky-200">
            <Sparkles className="h-5 w-5" />
          </div>
          {!collapsed && (
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-sky-300">SchemeSathi</p>
              <p className="text-sm text-slate-300">Benefits Navigator</p>
            </div>
          )}
        </div>
      </div>

      <nav className="space-y-2">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.label}
              type="button"
              className={cn(
                'flex w-full items-center gap-3 rounded-2xl border border-transparent bg-transparent px-3 py-3 text-left text-slate-200 transition hover:border-slate-700 hover:bg-slate-900/80',
                collapsed && 'justify-center px-2',
              )}
            >
              <Icon className="h-4 w-4 text-sky-200" />
              {!collapsed && <span className="text-sm font-medium">{item.label}</span>}
            </button>
          );
        })}
      </nav>

      {!collapsed && (
        <div className="mt-auto rounded-2xl border border-slate-800 bg-slate-900/80 p-4 text-sm text-slate-300">
          Profile completeness and saved artifacts will be surfaced here in the next phase.
        </div>
      )}
    </div>
  );
}
