"use client";

import { useEffect } from 'react';
import { useArtifactStore } from '@/store/artifactStore';
import { mockArtifacts } from './ArtifactRegistry';
import { ArtifactCard } from './ArtifactCard';
import { ArtifactDetailView } from './ArtifactDetailView';

export function ArtifactPanel() {
  const items = useArtifactStore((state) => state.items);
  const addArtifact = useArtifactStore((state) => state.addArtifact);
  const selectedId = useArtifactStore((state) => state.selectedId);

  useEffect(() => {
    if (items.length === 0) {
      mockArtifacts.forEach((artifact) => {
        addArtifact({
          id: artifact.id,
          type: artifact.type,
          title: artifact.title,
          summary: artifact.summary,
          status: artifact.status,
        });
      });
    }
  }, [addArtifact, items.length]);

  return (
    <aside className="space-y-4">
      <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-4 shadow-soft">
        <p className="text-xs uppercase tracking-[0.28em] text-violet-300">Mock Artifacts</p>
        <h3 className="mt-2 text-base font-semibold text-white">Artifact panel</h3>
        <p className="mt-2 text-sm text-slate-300">Mock artifact cards are now available in the right panel. Selection behavior is wired through the artifact store.</p>
      </div>

      <div className="space-y-3">
        {items.map((item) => (
          <ArtifactCard
            key={item.id}
            id={item.id}
            title={item.title}
            summary={item.summary}
            type={item.type}
            status={item.status}
          />
        ))}
      </div>

      {selectedId ? <ArtifactDetailView /> : null}
    </aside>
  );
}
