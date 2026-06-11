"use client";

import * as React from 'react';
import { useWorkspaceStore, type ViewportMode } from '@/store/workspaceStore';

export function ResponsiveShell({ children }: { children: React.ReactNode }) {
  const setViewport = useWorkspaceStore((state) => state.setViewport);

  React.useEffect(() => {
    const updateViewport = () => {
      const width = window.innerWidth;
      if (width < 768) setViewport('mobile');
      else if (width < 1280) setViewport('tablet');
      else setViewport('desktop');
    };

    updateViewport();
    window.addEventListener('resize', updateViewport);

    return () => window.removeEventListener('resize', updateViewport);
  }, [setViewport]);

  return <>{children}</>;
}
