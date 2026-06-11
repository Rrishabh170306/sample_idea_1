import { create } from 'zustand';

export interface ArtifactItem {
  id: string;
  type: 'eligibility' | 'scheme' | 'comparison' | 'checklist';
  title: string;
  summary: string;
  status: 'ready' | 'generating' | 'stale';
}

interface ArtifactState {
  items: ArtifactItem[];
  selectedId: string | null;
  addArtifact: (artifact: ArtifactItem) => void;
  selectArtifact: (id: string | null) => void;
  markGenerating: (id: string) => void;
}

export const useArtifactStore = create<ArtifactState>((set) => ({
  items: [],
  selectedId: null,
  addArtifact: (artifact) =>
    set((state) => ({
      items: [artifact, ...state.items.filter((item) => item.id !== artifact.id)],
      selectedId: state.selectedId ?? artifact.id,
    })),
  selectArtifact: (selectedId) => set({ selectedId }),
  markGenerating: (id) =>
    set((state) => ({
      items: state.items.map((item) => (item.id === id ? { ...item, status: 'generating' } : item)),
    })),
}));
