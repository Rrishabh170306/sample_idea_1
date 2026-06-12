"use client";

import Link from 'next/link';
import { useSession } from 'next-auth/react';
import * as React from 'react';
import { sendChatMessage } from '@/lib/chat/service';
import type { FrontendChatMessage } from '@/lib/chat/types';
import { isProfileComplete, loadSession, saveSession } from './session';

const starterMessages: FrontendChatMessage[] = [
  {
    role: 'assistant',
    text: 'I can help you find Indian welfare schemes based on your profile, documents, and questions.',
    meta: 'Grounded on your saved profile',
  },
];

export function ChatTemplate() {
  const { data: authSession, status } = useSession();
  const [session, setSession] = React.useState(() => loadSession());
  const [messages, setMessages] = React.useState<FrontendChatMessage[]>(starterMessages);
  const [draft, setDraft] = React.useState('What schemes am I eligible for?');
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
  };

  return (
    <section className="chat-shell chat-template" aria-label="Chat interface preview">
      <div className="chat-header">
        <div>
          <p className="eyebrow">SchemeSathi Chatbot</p>
          <h2 className="chat-title">Welfare schemes, directly through conversation</h2>
        </div>
        <div className="pill-row">
          <span className="pill">Profile: {isProfileComplete(session) ? 'Ready' : 'Pending'}</span>
          <span className="pill">Auth: {status === 'authenticated' ? 'Signed in' : 'Guest'}</span>
          <span className="pill">Voice: {voiceEnabled ? 'On' : 'Off'}</span>
          <span className="pill">Lang: {language}</span>
        </div>
      </div>

      <div className="message-stack" aria-live="polite">
        {messages.map((message, index) => (
          <article key={`${message.role}-${index}`} className={`message-card ${message.role}`}>
            {message.meta ? <p className="message-meta">{message.meta}</p> : null}
            <p>{message.text}</p>
          </article>
        ))}
      </div>

      {selectedFiles.length ? (
        <div className="upload-chip-wrap">
          {selectedFiles.map((file) => (
            <span key={file} className="pill">
              {file}
            </span>
          ))}
        </div>
      ) : null}

      <div className="composer">
        <input
          className="text-field composer-input"
          placeholder="Type your message..."
          aria-label="Chat message input"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              void sendMessage();
            }
          }}
        />

        <div className="composer-actions">
          <label className="pill upload-button">
            Upload PDF or Image
            <input
              type="file"
              multiple
              accept=".pdf,.docx,.jpg,.jpeg,.png"
              onChange={handleFileUpload}
              style={{ display: 'none' }}
            />
          </label>

          <select className="pill select-pill" value={language} onChange={(event) => setLanguage(event.target.value)}>
            <option value="English">English</option>
            <option value="Hindi">Hindi</option>
            <option value="Tamil">Tamil</option>
            <option value="Telugu">Telugu</option>
            <option value="Marathi">Marathi</option>
          </select>

          <button type="button" className="pill toggle-pill" onClick={() => setVoiceEnabled((current) => !current)}>
            {voiceEnabled ? 'Voice On' : 'Voice Off'}
          </button>
        </div>

        <button type="button" className="primary-button send-button" onClick={() => void sendMessage()} disabled={isSending}>
          {isSending ? 'Sending...' : 'Send'}
        </button>
      </div>

      {errorMessage ? <p className="helper-text">{errorMessage}</p> : null}
      {retryMessage ? (
        <div className="action-row">
          <button type="button" className="btn" onClick={() => void sendMessage(retryMessage, true)} disabled={isSending}>
            Retry
          </button>
        </div>
      ) : null}

      <p className="helper-text">
        <Link href="/auth">Login</Link> first, then complete your profile for better eligibility results.
      </p>
    </section>
  );
}
