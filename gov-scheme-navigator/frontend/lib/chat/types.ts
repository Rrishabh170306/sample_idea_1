// ─── Basic chat message types ────────────────────────────────────────────────

export type FrontendChatMessage = {
  role: 'user' | 'assistant';
  text: string;
  meta?: string;
  schemes?: SchemeResult[];
  eligibility?: Record<string, EligibilityInfo>;
  citations?: Citation[];
  queryType?: string;
};

// ─── API request/response shapes ─────────────────────────────────────────────

export type ChatRequest = {
  message: string;
  session_id?: string;
  user_id?: string;
  user_profile?: Record<string, unknown>;
};

export type SchemeResult = {
  scheme_id: string;
  name: string;
  source: string;
  score: number;
  metadata: Record<string, unknown>;
};

export type EligibilityInfo = {
  eligible: boolean;
  score: number;
  explanation: string;
  gaps: Array<Record<string, unknown>>;
};

export type Citation = {
  source_url?: string;
  title?: string;
  [key: string]: unknown;
};

export type ChatResponse = {
  reply: string;
  session_id: string;
  user_email?: string | null;
  schemes: SchemeResult[];
  eligibility: Record<string, EligibilityInfo>;
  citations: Citation[];
  query_type: string;
};

// ─── Service layer types ─────────────────────────────────────────────────────

export type ChatServiceInput = {
  message: string;
  sessionId?: string;
  userEmail?: string | null;
  userProfile?: Record<string, unknown>;
};

export type ChatServiceResult = {
  text: string;
  meta?: string;
  sessionId?: string | null;
  schemes: SchemeResult[];
  eligibility: Record<string, EligibilityInfo>;
  citations: Citation[];
  queryType: string;
};
