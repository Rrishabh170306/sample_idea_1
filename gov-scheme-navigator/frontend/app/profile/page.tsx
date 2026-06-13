import { ProfileForm } from '@/components/chatbot/ProfileForm';
import { ProtectedRoute } from '@/components/chatbot/ProtectedRoute';

export default function ProfileSetupPage() {
  return (
    <main className="onboarding-shell profile-shell">
      <ProtectedRoute>
        <ProfileForm />
      </ProtectedRoute>
    </main>
  );
}
