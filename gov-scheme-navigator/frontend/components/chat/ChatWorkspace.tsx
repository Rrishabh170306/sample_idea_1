"use client";

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { AgentStatusBanner } from './AgentStatusBanner';
import { MessageRenderer } from './MessageRenderer';
import { useMockChatStream } from '@/hooks/useMockChatStream';

export function ChatWorkspace() {
  const [input, setInput] = React.useState('What schemes am I eligible for?');
  const { run, status, text, citations, isStreaming, error } = useMockChatStream();

  return (
    <section className="flex h-full flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-950/80 p-4 shadow-soft">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
        <p className="text-xs uppercase tracking-[0.28em] text-sky-300">Chat</p>
        <h3 className="mt-1 text-lg font-semibold text-white">Mock Streaming Chat</h3>
        <p className="mt-2 text-sm text-slate-300">This phase focuses on streaming status transitions, markdown rendering, and citation placeholders only.</p>
      </div>

      <AgentStatusBanner status={status} isStreaming={isStreaming} />

      <div className="flex-1 space-y-4 overflow-y-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4">
        <article className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 text-sm text-slate-100">
          <p className="text-xs uppercase tracking-[0.25em] text-slate-400">User</p>
          <p className="mt-2 text-slate-100">{input}</p>
        </article>

        {text ? <MessageRenderer text={text} citations={citations} /> : null}

        {error ? (
          <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-100">
            {error}
          </div>
        ) : null}
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          className="min-h-[88px] w-full rounded-2xl border border-slate-700 bg-slate-950/90 px-4 py-3 text-sm text-slate-100 outline-none ring-0 transition focus:border-sky-400"
          placeholder="Ask about scheme eligibility, comparisons, or application steps"
        />

        <div className="mt-3 flex items-center justify-between gap-3">
          <p className="text-xs text-slate-400">Status flow: Thinking → Retrieving → Verifying → Finalizing</p>
          <Button
            type="button"
            onClick={() => run(input)}
            disabled={isStreaming}
            className="bg-sky-500/90 text-slate-950 hover:bg-sky-400"
          >
            {isStreaming ? 'Streaming…' : 'Run Mock Stream'}
          </Button>
        </div>
      </div>
    </section>
  );
}
