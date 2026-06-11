import { create } from 'zustand';

export type ViewportMode = 'desktop' | 'tablet' | 'mobile';

interface WorkspaceState {
  sidebarOpen: boolean;
  artifactPanelOpen: boolean;
  viewport: ViewportMode;
  activeSessionId: string | null;
  setSidebarOpen: (open: boolean) => void;
  setArtifactPanelOpen: (open: boolean) => void;
  setViewport: (viewport: ViewportMode) => void;
  setActiveSessionId: (sessionId: string | null) => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  sidebarOpen: true,
  artifactPanelOpen: true,
  viewport: 'desktop',
  activeSessionId: 'session-demo',
  setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
  setArtifactPanelOpen: (artifactPanelOpen) => set({ artifactPanelOpen }),
  setViewport: (viewport) => set({ viewport }),
  setActiveSessionId: (activeSessionId) => set({ activeSessionId }),
}));
