"use client";

import { PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen } from 'lucide-react';
import { EmptyState } from './EmptyState';
import { SidebarNav } from './SidebarNav';
import { TopBar } from './TopBar';
import { ChatWorkspace } from '@/components/chat/ChatWorkspace';
import { ArtifactPanel } from '@/components/artifacts/ArtifactPanel';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export function WorkspaceShell() {
  const sidebarOpen = useWorkspaceStore((state) => state.sidebarOpen);
  const artifactPanelOpen = useWorkspaceStore((state) => state.artifactPanelOpen);
  const setSidebarOpen = useWorkspaceStore((state) => state.setSidebarOpen);
  const setArtifactPanelOpen = useWorkspaceStore((state) => state.setArtifactPanelOpen);

  return (
    <main className="min-h-screen bg-transparent text-slate-100">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-4 py-4 lg:px-6">
        <TopBar />

        <section className="mt-4 flex min-h-[calc(100vh-6rem)] flex-1 gap-4 rounded-3xl border border-slate-800 bg-slate-950/80 p-4 shadow-soft backdrop-blur xl:p-6">
          <aside
            className={cn(
              'hidden shrink-0 border-r border-slate-800 pr-4 transition-all duration-200 lg:block',
              sidebarOpen ? 'w-80' : 'w-20',
            )}
          >
            <SidebarNav collapsed={!sidebarOpen} />
          </aside>

          <div className="flex min-w-0 flex-1 flex-col rounded-2xl border border-slate-800 bg-slate-900/70">
            <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-sky-300">Workspace</p>
                <h2 className="text-lg font-semibold text-white">SchemeSathi</h2>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  onClick={() => setSidebarOpen(!sidebarOpen)}
                  className="hidden lg:inline-flex"
                >
                  {sidebarOpen ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeftOpen className="h-4 w-4" />}
                </Button>
                <Button
                  type="button"
                  onClick={() => setArtifactPanelOpen(!artifactPanelOpen)}
                  className="hidden xl:inline-flex"
                >
                  {artifactPanelOpen ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
                </Button>
              </div>
            </div>

            <div className="flex flex-1 flex-col overflow-hidden p-4 lg:flex-row lg:p-6">
              <section className="flex-1 overflow-y-auto rounded-2xl border border-slate-800 bg-slate-950/70 p-5">
                <ChatWorkspace />
              </section>

              {artifactPanelOpen ? (
                <aside className="mt-4 w-full shrink-0 border-t border-slate-800 pt-4 lg:mt-0 lg:ml-4 lg:w-96 lg:border-l lg:border-t-0 lg:pl-4 lg:pt-0 xl:w-[420px]">
                  <ArtifactPanel />
                </aside>
              ) : null}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
