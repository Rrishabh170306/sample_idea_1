"use client";

import { useArtifactStore } from '@/store/artifactStore';
import { getMockArtifact } from './ArtifactRegistry';
import { EligibilityReportView } from './EligibilityReportView';
import { SchemeDetailView } from './SchemeDetailView';
import { SchemeComparisonView } from './SchemeComparisonView';
import { ApplicationChecklistView } from './ApplicationChecklistView';

export function ArtifactDetailView() {
  const selectedId = useArtifactStore((state) => state.selectedId);
  const items = useArtifactStore((state) => state.items);

  const selectedArtifact = items.find((item) => item.id === selectedId) ?? items[0];
  if (!selectedArtifact) return null;

  const detail = getMockArtifact(selectedArtifact.type);

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-slate-100 shadow-soft">
      <p className="text-xs uppercase tracking-[0.28em] text-violet-300">Artifact Detail</p>
      <h3 className="mt-2 text-xl font-semibold text-white">{selectedArtifact.title}</h3>
      <p className="mt-2 text-sm text-slate-300">{selectedArtifact.summary}</p>

      {selectedArtifact.type === 'eligibility' && <EligibilityReportView artifact={detail} />}
      {selectedArtifact.type === 'scheme' && <SchemeDetailView artifact={detail} />}
      {selectedArtifact.type === 'comparison' && <SchemeComparisonView artifact={detail} />}
      {selectedArtifact.type === 'checklist' && <ApplicationChecklistView artifact={detail} />}
    </section>
  );
}
