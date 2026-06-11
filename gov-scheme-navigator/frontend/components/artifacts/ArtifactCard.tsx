"use client";

import { FileText, Shield, Layers3, ListChecks } from 'lucide-react';
import { useArtifactStore } from '@/store/artifactStore';

interface ArtifactCardProps {
  id: string;
  title: string;
  summary: string;
  type: 'eligibility' | 'scheme' | 'comparison' | 'checklist';
  status: 'ready' | 'generating' | 'stale';
}

const iconMap = {
  eligibility: Shield,
  scheme: FileText,
  comparison: Layers3,
  checklist: ListChecks,
};

export function ArtifactCard({ id, title, summary, type, status }: ArtifactCardProps) {
  const selectedId = useArtifactStore((state) => state.selectedId);
  const selectArtifact = useArtifactStore((state) => state.selectArtifact);
  const Icon = iconMap[type];

  return (
    <button
      type="button"
      onClick={() => selectArtifact(id)}
      className={`w-full rounded-2xl border p-4 text-left transition ${
        selectedId === id
          ? 'border-sky-400 bg-sky-400/10'
          : 'border-slate-800 bg-slate-950/80 hover:border-slate-700 hover:bg-slate-900'
      }`}
    >
      <div className="flex items-center gap-3">
        <div className="rounded-xl bg-slate-900 p-2 text-sky-200">
          <Icon className="h-4 w-4" />
        </div>
        <div>
          <p className="text-sm font-semibold text-white">{title}</p>
          <p className="text-xs text-slate-400">{summary}</p>
        </div>
      </div>
      <p className="mt-3 text-xs uppercase tracking-[0.25em] text-slate-400">Status: {status}</p>
    </button>
  );
}
