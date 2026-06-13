"use client";

import { Mic, Paperclip, SendHorizontal, X } from 'lucide-react';
import { useSession } from 'next-auth/react';
import * as React from 'react';
import { sendChatMessage } from '@/lib/chat/service';
import type { FrontendChatMessage } from '@/lib/chat/types';
import { isProfileComplete, loadSession, saveSession } from './session';

const suggestedPrompts = [
  'What schemes am I eligible for?',
  'Compare PM-KISAN and Kisan Credit Card',
  'What documents do I need?',
];

export function ChatTemplate() {
  const { data: authSession, status } = useSession();
  const [session, setSession] = React.useState(() => loadSession());
  const [messages, setMessages] = React.useState<FrontendChatMessage[]>([]);
  const [draft, setDraft] = React.useState('');
  const [selectedFiles, setSelectedFiles] = React.useState<string[]>([]);
  const [language, setLanguage] = React.useState(session.language || 'English');
  const [voiceEnabled, setVoiceEnabled] = React.useState(session.voiceEnabled);
  const [isSending, setIsSending] = React.useState(false);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);
  const [retryMessage, setRetryMessage] = React.useState<string | null>(null);
  const sessionIdRef = React.useRef<string>(crypto.randomUUID());

  React.useEffect(() => {
    setSession(loadSession());
  }, []);

  React.useEffect(() => {
    saveSession({ ...session, language, voiceEnabled });
  }, [language, session, voiceEnabled]);

  const sendMessage = async (messageOverride?: string, reuseExistingUserMessage = false) => {
    const trimmed = (messageOverride ?? draft).trim();
    if (!trimmed) {
      return;
    }

    setIsSending(true);
    setErrorMessage(null);
    setRetryMessage(null);

    if (!reuseExistingUserMessage) {
      setMessages((current) => [...current, { role: 'user', text: trimmed }]);
    }
    setDraft('');

    try {
      const result = await sendChatMessage({
        message: trimmed,
        sessionId: sessionIdRef.current,
        userEmail: authSession?.user?.email,
      });
      const fileNote = selectedFiles.length ? ` I have noted ${selectedFiles.length} uploaded document(s).` : '';
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          text: `${result.text}${fileNote}`,
          meta: result.meta,
        },
      ]);
      if (result.sessionId) {
        sessionIdRef.current = result.sessionId;
      }
    } catch {
      setErrorMessage('Could not reach the chat service. Please try again.');
      setRetryMessage(trimmed);
    } finally {
      setIsSending(false);
    }
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []).map((file) => file.name);
    setSelectedFiles((current) => [...current, ...files]);
    event.target.value = '';
  };

  const removeFile = (fileName: string) => {
    setSelectedFiles((current) => current.filter((file) => file !== fileName));
  };

  return (
    <section className="assistant-chat" aria-label="SchemeSathi chat">
      <header className="assistant-topbar">
        <div>
          <p className="assistant-brand">SchemeSathi</p>
          <p className="assistant-subtitle">Government scheme assistant</p>
        </div>
        <div className="assistant-status-row" aria-label="Session status">
          <span className="assistant-status">{isProfileComplete(session) ? 'Profile ready' : 'Profile pending'}</span>
          <span className="assistant-status">{status === 'authenticated' ? 'Signed in' : 'Guest'}</span>
        </div>
      </header>

      <div className="message-stack" aria-live="polite">
        {messages.length === 0 ? (
          <div className="chat-empty-state">
            <p className="empty-brand">SchemeSathi</p>
            <h1>Your government scheme assistant</h1>
            <p className="empty-copy">Ask about eligibility, documents, applications, or compare schemes in one conversation.</p>
            <div className="suggested-prompts" aria-label="Suggested prompts">
              {suggestedPrompts.map((prompt) => (
                <button key={prompt} type="button" className="suggested-prompt" onClick={() => void sendMessage(prompt)}>
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <article key={`${message.role}-${index}`} className={`message-card ${message.role}`}>
              {message.meta ? <p className="message-meta">{message.meta}</p> : null}
              <p>{message.text}</p>
            </article>
          ))
        )}
      </div>

      <footer className="composer-dock">
        {selectedFiles.length ? (
          <div className="upload-chip-wrap" aria-label="Attached files">
            {selectedFiles.map((file) => (
              <span key={file} className="attachment-chip">
                {file}
                <button type="button" aria-label={`Remove ${file}`} onClick={() => removeFile(file)}>
                  <X size={14} aria-hidden="true" />
                </button>
              </span>
            ))}
          </div>
        ) : null}

        {errorMessage ? <p className="composer-note status-error">{errorMessage}</p> : null}
        {retryMessage ? (
          <button type="button" className="retry-button" onClick={() => void sendMessage(retryMessage, true)} disabled={isSending}>
            Retry last message
          </button>
        ) : null}

        <div className="composer">
          <label className="composer-icon-button upload-button" title="Attach document" aria-label="Attach document">
            <Paperclip size={20} aria-hidden="true" />
            <input type="file" multiple accept=".pdf,.docx,.jpg,.jpeg,.png" onChange={handleFileUpload} />
          </label>

          <input
            className="composer-input"
            placeholder="Ask about schemes, eligibility, or documents..."
            aria-label="Chat message input"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                void sendMessage();
              }
            }}
          />

          <select className="language-select" aria-label="Response language" value={language} onChange={(event) => setLanguage(event.target.value)}>
            <option value="English">EN</option>
            <option value="Hindi">HI</option>
            <option value="Tamil">TA</option>
            <option value="Telugu">TE</option>
            <option value="Marathi">MR</option>
          </select>

          <button
            type="button"
            className={`composer-icon-button ${voiceEnabled ? 'active' : ''}`}
            title="Voice input"
            aria-label="Voice input"
            onClick={() => setVoiceEnabled((current) => !current)}
          >
            <Mic size={20} aria-hidden="true" />
          </button>

          <button type="button" className="composer-send-button" aria-label="Send message" onClick={() => void sendMessage()} disabled={isSending}>
            <SendHorizontal size={20} aria-hidden="true" />
          </button>
        </div>
      </footer>
    </section>
  );
}
