import type { ChatRequest, ChatResponse } from './types';

const DEFAULT_API_BASE_URL = 'http://localhost:8000';

function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL;
}

export async function postChatMessage(payload: ChatRequest, userEmail?: string | null): Promise<ChatResponse> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (userEmail) {
    headers['X-User-Email'] = userEmail;
  }

  const response = await fetch(`${getApiBaseUrl()}/api/v1/chat/messages`, {
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
