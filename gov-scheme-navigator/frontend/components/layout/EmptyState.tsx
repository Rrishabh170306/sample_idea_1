export function EmptyState() {
  return (
    <div className="flex h-full min-h-[320px] flex-col items-center justify-center rounded-3xl border border-dashed border-slate-700 bg-slate-950/70 px-6 text-center">
      <p className="text-xs uppercase tracking-[0.35em] text-sky-300">Phase 1</p>
      <h3 className="mt-3 text-2xl font-semibold text-white">Workspace foundation is ready</h3>
      <p className="mt-3 max-w-xl text-sm text-slate-300">
        This shell establishes the responsive workspace, artifact-ready panel, profile sidebar area, theme setup, and state foundation for the next frontend phases.
      </p>
      <div className="mt-6 flex flex-wrap items-center justify-center gap-3 text-xs text-slate-200">
        <span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1">Next.js App Router</span>
        <span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1">TypeScript</span>
        <span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1">Tailwind + ShadCN-style UI</span>
      </div>
    </div>
  );
}
