"use client";

import Link from 'next/link';
import { useSession } from 'next-auth/react';
import * as React from 'react';
import { sendChatMessage } from '@/lib/chat/service';
import type {
  Citation,
  EligibilityInfo,
  FrontendChatMessage,
  SchemeResult,
} from '@/lib/chat/types';
import { isProfileComplete, loadSession, saveSession } from './session';

const starterMessages: FrontendChatMessage[] = [
  {
    role: 'assistant',
    text: 'Namaste! I can help you find Indian government welfare schemes you are eligible for. Tell me about yourself — your state, occupation, age, income, and what kind of help you need.',
    meta: 'Powered by Gov-Scheme-Navigator AI',
    schemes: [],
    eligibility: {},
    citations: [],
  },
];

// ── Scheme Card Component ────────────────────────────────────────────────────
function SchemeCard({ scheme, eligibility }: { scheme: SchemeResult; eligibility?: EligibilityInfo }) {
  const isEligible = eligibility?.eligible;
  const eligibilityKnown = eligibility !== undefined;

  return (
    <div className="scheme-card" role="article" aria-label={`Scheme: ${scheme.name}`}>
      <div className="scheme-card-header">
        <span className="scheme-name">{scheme.name}</span>
        {eligibilityKnown && (
          <span className={`eligibility-badge ${isEligible ? 'eligible' : 'not-eligible'}`}>
            {isEligible ? '✓ Eligible' : '✗ Not confirmed'}
          </span>
        )}
      </div>

      {eligibility?.explanation && (
        <p className="scheme-explanation">{eligibility.explanation}</p>
      )}

      {eligibility?.score !== undefined && (
        <div className="scheme-score-bar">
          <div
            className="scheme-score-fill"
            style={{ width: `${Math.round(eligibility.score * 100)}%` }}
          />
          <span className="scheme-score-label">
            Match: {Math.round(eligibility.score * 100)}%
          </span>
        </div>
      )}

      {scheme.metadata?.official_url && (
        <a
          href={scheme.metadata.official_url as string}
          target="_blank"
          rel="noopener noreferrer"
          className="scheme-link"
        >
          Apply / Learn more →
        </a>
      )}
    </div>
  );
}

// ── Citations Component ──────────────────────────────────────────────────────
function CitationList({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null;
  return (
    <div className="citation-list">
      <p className="citation-label">Sources:</p>
      <ul>
        {citations.map((c, i) => (
          <li key={i}>
            {c.source_url ? (
              <a href={c.source_url} target="_blank" rel="noopener noreferrer" className="citation-link">
                {c.title || c.source_url}
              </a>
            ) : (
              <span>{c.title || JSON.stringify(c)}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

// ── Message Bubble ────────────────────────────────────────────────────────────
function MessageBubble({ message, index }: { message: FrontendChatMessage; index: number }) {
  return (
    <article
      key={`${message.role}-${index}`}
      className={`message-card ${message.role}`}
      aria-label={`${message.role === 'user' ? 'You' : 'Assistant'}: ${message.text.slice(0, 50)}`}
    >
      {message.meta && <p className="message-meta">{message.meta}</p>}
      <p className="message-text">{message.text}</p>

      {message.schemes && message.schemes.length > 0 && (
        <div className="scheme-results" aria-label="Matched schemes">
          <p className="scheme-results-heading">Matched Schemes:</p>
          {message.schemes.map((scheme) => (
            <SchemeCard
              key={scheme.scheme_id || scheme.name}
              scheme={scheme}
              eligibility={message.eligibility?.[scheme.scheme_id]}
            />
          ))}
        </div>
      )}

      {message.citations && message.citations.length > 0 && (
        <CitationList citations={message.citations} />
      )}
    </article>
  );
}

// ── Main ChatTemplate ─────────────────────────────────────────────────────────
export function ChatTemplate() {
  const { data: authSession, status } = useSession();
  const [session, setSession] = React.useState(() => loadSession());
  const [messages, setMessages] = React.useState<FrontendChatMessage[]>(starterMessages);
  const [draft, setDraft] = React.useState('');
  const [language, setLanguage] = React.useState(session.language || 'English');
  const [voiceEnabled, setVoiceEnabled] = React.useState(session.voiceEnabled);
  const [isSending, setIsSending] = React.useState(false);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);
  const [retryMessage, setRetryMessage] = React.useState<string | null>(null);
  const sessionIdRef = React.useRef<string>(crypto.randomUUID());
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  // Scroll to bottom when new messages arrive
  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  React.useEffect(() => {
    setSession(loadSession());
  }, []);

  React.useEffect(() => {
    saveSession({ ...session, language, voiceEnabled });
  }, [language, session, voiceEnabled]);

  const sendMessage = async (messageOverride?: string, reuseExistingUserMessage = false) => {
    const trimmed = (messageOverride ?? draft).trim();
    if (!trimmed || isSending) return;

    setIsSending(true);
    setErrorMessage(null);
    setRetryMessage(null);

    if (!reuseExistingUserMessage) {
      setMessages((current) => [...current, { role: 'user', text: trimmed, schemes: [], eligibility: {}, citations: [] }]);
    }
    setDraft('');

    // Build user profile from session if available
    const userProfile: Record<string, unknown> = {};
    if (session.state) userProfile.state = session.state;
    if (session.occupation) userProfile.occupation = session.occupation;
    if (session.age) userProfile.age = session.age;
    if (session.income) userProfile.income = session.income;

    try {
      const result = await sendChatMessage({
        message: trimmed,
        sessionId: sessionIdRef.current,
        userEmail: authSession?.user?.email,
        userProfile: Object.keys(userProfile).length > 0 ? userProfile : undefined,
      });

      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          text: result.text,
          meta: result.meta,
          schemes: result.schemes,
          eligibility: result.eligibility,
          citations: result.citations,
          queryType: result.queryType,
        },
      ]);

      if (result.sessionId) {
        sessionIdRef.current = result.sessionId;
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setErrorMessage(`Could not reach the chat service: ${msg}`);
      setRetryMessage(trimmed);
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      void sendMessage();
    }
  };

  // Quick starter prompts
  const starterPrompts = [
    'I am a farmer from Tamil Nadu with 3 acres land',
    'What schemes exist for women entrepreneurs?',
    'Education scholarships for SC/ST students',
    'PM-KISAN eligibility for small farmers',
  ];

  return (
    <section className="chat-shell chat-template" aria-label="Scheme Navigator Chat">
      <div className="chat-header">
        <div>
          <p className="eyebrow">SchemeSathi · AI Assistant</p>
          <h2 className="chat-title">Find welfare schemes you qualify for</h2>
        </div>
        <div className="pill-row">
          <span className="pill">Profile: {isProfileComplete(session) ? '✓ Ready' : '⚠ Pending'}</span>
          <span className="pill">Auth: {status === 'authenticated' ? '✓ Signed in' : 'Guest'}</span>
          <span className="pill">Lang: {language}</span>
        </div>
      </div>

      {/* Starter prompts — hidden once user has sent a message */}
      {messages.length <= 1 && (
        <div className="starter-prompts" aria-label="Suggested questions">
          {starterPrompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              className="pill prompt-chip"
              onClick={() => {
                setDraft(prompt);
              }}
            >
              {prompt}
            </button>
          ))}
        </div>
      )}

      {/* Message thread */}
      <div className="message-stack" aria-live="polite" aria-label="Chat messages">
        {messages.map((message, index) => (
          <MessageBubble key={`${message.role}-${index}`} message={message} index={index} />
        ))}

        {/* Typing indicator */}
        {isSending && (
          <div className="message-card assistant typing-indicator" aria-label="Assistant is thinking">
            <span />
            <span />
            <span />
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Error / Retry */}
      {errorMessage && (
        <div className="error-banner" role="alert">
          <p>{errorMessage}</p>
          {retryMessage && (
            <button
              type="button"
              className="btn"
              onClick={() => void sendMessage(retryMessage, true)}
              disabled={isSending}
            >
              Retry
            </button>
          )}
        </div>
      )}

      {/* Composer */}
      <div className="composer">
        <input
          id="chat-input"
          className="text-field composer-input"
          placeholder="Ask about schemes, eligibility, or documents..."
          aria-label="Chat message input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isSending}
          autoComplete="off"
        />

        <div className="composer-actions">
          <select
            className="pill select-pill"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            aria-label="Select language"
          >
            <option value="English">English</option>
            <option value="Hindi">हिन्दी</option>
            <option value="Tamil">தமிழ்</option>
            <option value="Telugu">తెలుగు</option>
            <option value="Marathi">मराठी</option>
            <option value="Bengali">বাংলা</option>
          </select>

          <button
            type="button"
            className="pill toggle-pill"
            onClick={() => setVoiceEnabled((v) => !v)}
            aria-label={voiceEnabled ? 'Disable voice' : 'Enable voice'}
          >
            {voiceEnabled ? '🔊 Voice On' : '🔇 Voice Off'}
          </button>
        </div>

        <button
          id="chat-send-button"
          type="button"
          className="primary-button send-button"
          onClick={() => void sendMessage()}
          disabled={isSending || !draft.trim()}
          aria-label="Send message"
        >
          {isSending ? 'Thinking...' : 'Send →'}
        </button>
      </div>

      <p className="helper-text">
        <Link href="/profile">Complete your profile</Link> for more accurate eligibility results.
        All data is processed securely.
      </p>
    </section>
  );
}
