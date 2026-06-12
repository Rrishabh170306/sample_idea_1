import { AuthPanel } from '@/components/chatbot/AuthPanel';

export default function AuthPage() {
  return (
    <main className="app-shell">
      <section className="surface main-pad">
        <AuthPanel />
      </section>
    </main>
  );
}
