export type FrontendChatMessage = {
  role: 'user' | 'assistant';
  text: string;
  meta?: string;
};

export type ChatRequest = {
  message: string;
  session_id?: string;
};

export type ChatResponse = {
  reply: string;
  session_id?: string | null;
  user_email?: string | null;
};

export type ChatServiceInput = {
  message: string;
  sessionId?: string;
  userEmail?: string | null;
};

export type ChatServiceResult = {
  text: string;
  meta?: string;
  sessionId?: string | null;
};
