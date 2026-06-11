"use client";

import { Bell, Search, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function TopBar() {
  return (
    <header className="flex items-center justify-between rounded-3xl border border-slate-800 bg-slate-950/70 px-4 py-3 shadow-soft backdrop-blur lg:px-5">
      <div>
        <p className="text-xs uppercase tracking-[0.35em] text-sky-300">SchemeSathi</p>
        <h1 className="text-xl font-semibold text-white">Government Scheme Navigator</h1>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 transition hover:border-slate-500 hover:bg-slate-800"
        >
          <Search className="h-4 w-4 text-sky-200" />
          Quick search
        </button>
        <Button type="button" className="hidden md:inline-flex">
          <Bell className="mr-2 h-4 w-4" /> Alerts
        </Button>
        <Button type="button" className="hidden md:inline-flex">
          <Settings className="mr-2 h-4 w-4" /> Settings
        </Button>
      </div>
    </header>
  );
}
