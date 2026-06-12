import { mapChatResponseToMessage } from './adapter';
import { postChatMessage } from './api';
import type { ChatServiceInput, ChatServiceResult } from './types';

export async function sendChatMessage(input: ChatServiceInput): Promise<ChatServiceResult> {
  const response = await postChatMessage(
    {
      message: input.message,
      session_id: input.sessionId,
      user_profile: input.userProfile,
    },
    input.userEmail,
  );
  return mapChatResponseToMessage(response);
}
