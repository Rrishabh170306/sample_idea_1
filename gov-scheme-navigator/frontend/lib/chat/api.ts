import type { ChatRequest, ChatResponse } from './types';

export async function postChatMessage(payload: ChatRequest, userEmail?: string | null): Promise<ChatResponse> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  const response = await fetch('/api/backend/chat/messages', {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Chat request failed with status ${response.status}`);
  }

  return response.json() as Promise<ChatResponse>;
}
