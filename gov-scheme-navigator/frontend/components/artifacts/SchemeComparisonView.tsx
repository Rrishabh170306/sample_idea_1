"use client";

import type { MockArtifact } from './ArtifactRegistry';

export function SchemeComparisonView({ artifact }: { artifact: MockArtifact }) {
  return (
    <div className="mt-4 space-y-3 rounded-2xl border border-slate-800 bg-slate-900/80 p-4 text-sm text-slate-100">
      <p className="text-xs uppercase tracking-[0.25em] text-violet-300">Scheme Comparison</p>
      <ul className="space-y-2 text-slate-200">
        {artifact.details.map((item) => (
          <li key={item} className="rounded-xl border border-slate-800 bg-slate-950/70 p-3">{item}</li>
        ))}
      </ul>
    </div>
  );
}
