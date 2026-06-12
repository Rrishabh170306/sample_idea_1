import type { ChatResponse, ChatServiceResult } from './types';

export function mapChatResponseToMessage(response: ChatResponse): ChatServiceResult {
  return {
    text: response.reply,
    meta: response.user_email ? `Backend response for ${response.user_email}` : 'Backend response',
    sessionId: response.session_id ?? null,
  };
}
