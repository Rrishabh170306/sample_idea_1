"use client";

import * as React from 'react';

interface MessageRendererProps {
  text: string;
  citations?: Array<{ id: string; label: string; source: string }>;
}

function renderMarkdown(text: string) {
  return text
    .split('\n')
    .map((line) => {
      if (line.startsWith('- ')) return `<li>${line.slice(2)}</li>`;
      return line ? `<p>${line}</p>` : '<br />';
    })
    .join('');
}

export function MessageRenderer({ text, citations = [] }: MessageRendererProps) {
  return (
    <article className="space-y-3 rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-sm text-slate-100 shadow-soft">
      <div
        className="prose prose-invert max-w-none text-sm leading-6 text-slate-100"
        dangerouslySetInnerHTML={{ __html: renderMarkdown(text) }}
      />

      {citations.length > 0 && (
        <footer className="rounded-xl border border-slate-800 bg-slate-900/80 p-3 text-xs text-slate-300">
          <p className="mb-2 uppercase tracking-[0.25em] text-sky-300">Citations</p>
          <ul className="space-y-1">
            {citations.map((citation) => (
              <li key={citation.id} className="flex items-center gap-2">
                <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-sky-500/10 text-sky-200">{citation.id}</span>
                <span>{citation.label}</span>
                <span className="text-slate-400">— {citation.source}</span>
              </li>
            ))}
          </ul>
        </footer>
      )}
    </article>
  );
}
