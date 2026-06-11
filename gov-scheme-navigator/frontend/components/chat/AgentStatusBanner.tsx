"use client";

import { Loader2 } from 'lucide-react';
import type { ChatStatus } from '@/services/mockChatService';

interface AgentStatusBannerProps {
  status: ChatStatus;
  isStreaming: boolean;
}

export function AgentStatusBanner({ status, isStreaming }: AgentStatusBannerProps) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/90 p-3 text-sm text-slate-100 shadow-soft">
      <div className="flex items-center gap-3">
        <Loader2 className={`h-4 w-4 text-sky-200 ${isStreaming ? 'animate-spin' : ''}`} />
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-sky-300">Agent Status</p>
          <p className="text-sm text-slate-100">{status}</p>
        </div>
      </div>
    </div>
  );
}
