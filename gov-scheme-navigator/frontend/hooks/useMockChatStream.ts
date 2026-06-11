"use client";

import * as React from 'react';
import { simulateStream, type ChatStatus, type DemoResponse } from '@/services/mockChatService';
import { useArtifactStore } from '@/store/artifactStore';
import { mockArtifacts } from '@/components/artifacts/ArtifactRegistry';

export function useMockChatStream() {
  const addArtifact = useArtifactStore((state) => state.addArtifact);
  const [status, setStatus] = React.useState<ChatStatus>('Thinking');
  const [text, setText] = React.useState('');
  const [citations, setCitations] = React.useState<DemoResponse['citations']>([]);
  const [isStreaming, setIsStreaming] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const run = React.useCallback(async (input: string) => {
    setIsStreaming(true);
    setError(null);
    setText('');
    setCitations([]);

    try {
      const stream = await simulateStream(input);
      for await (const chunk of stream) {
        setStatus(chunk.status);
        setText((prev) => `${prev}${prev ? '\n\n' : ''}${chunk.text}`);
        if (chunk.citations.length) {
          setCitations(chunk.citations);
        }
      }

      mockArtifacts.forEach((artifact) => {
        addArtifact({
          id: artifact.id,
          type: artifact.type,
          title: artifact.title,
          summary: artifact.summary,
          status: 'ready',
        });
      });
    } catch (err) {
      setError('Streaming failed. Please try again.');
    } finally {
      setIsStreaming(false);
      setStatus('Finalizing');
    }
  }, []);

  return { run, status, text, citations, isStreaming, error };
}
