import type { ChatResponse, ChatServiceResult } from './types';

export function mapChatResponseToMessage(response: ChatResponse): ChatServiceResult {
  const metaParts: string[] = [];
  if (response.query_type && response.query_type !== 'general') {
    metaParts.push(`Query type: ${response.query_type}`);
  }
  if (response.user_email) {
    metaParts.push(`User: ${response.user_email}`);
  }
  if (response.schemes?.length) {
    metaParts.push(`${response.schemes.length} scheme(s) found`);
  }
  const eligibleCount = Object.values(response.eligibility ?? {}).filter(
    (e) => e.eligible
  ).length;
  if (eligibleCount > 0) {
    metaParts.push(`${eligibleCount} eligible`);
  }

  return {
    text: response.reply,
    meta: metaParts.length > 0 ? metaParts.join(' · ') : 'Backend response',
    sessionId: response.session_id ?? null,
    schemes: response.schemes ?? [],
    eligibility: response.eligibility ?? {},
    citations: response.citations ?? [],
    queryType: response.query_type ?? 'general',
  };
}
