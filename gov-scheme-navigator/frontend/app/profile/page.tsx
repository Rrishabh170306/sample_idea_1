import Link from 'next/link';
import { ProfileForm } from '@/components/chatbot/ProfileForm';
import { ProtectedRoute } from '@/components/chatbot/ProtectedRoute';

export default function ProfileSetupPage() {
  return (
    <main className="app-shell">
      <section className="surface main-pad">
        <ProtectedRoute>
          <ProfileForm />
          <div className="cta-row">
            <Link href="/auth" className="btn">
              Back to login
            </Link>
            <Link href="/chat" className="btn btn-primary">
              Continue to chatbot
            </Link>
          </div>
        </ProtectedRoute>
      </section>
    </main>
  );
}
