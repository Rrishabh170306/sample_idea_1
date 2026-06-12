import Link from 'next/link';
import { ChatTemplate } from '@/components/chatbot/ChatTemplate';

export default function ChatPage() {
  return (
    <main className="app-shell">
      <section className="surface main-pad">
        <div className="top-row">
          <h1 className="brand">Chatbot Workspace</h1>
          <Link href="/" className="btn">
            Home
          </Link>
        </div>

        <p className="subtitle">
          This Phase-2 workspace keeps the layout centered on chat, document upload, translation, and voice controls.
        </p>

        <ChatTemplate />
      </section>
    </main>
  );
}
