"use client";

import { useRouter } from 'next/navigation';
import { signIn, useSession } from 'next-auth/react';
import * as React from 'react';

export function AuthPanel() {
  const router = useRouter();
  const { status } = useSession();
  const [isLoading, setIsLoading] = React.useState(false);

  React.useEffect(() => {
    if (status === 'authenticated') {
      router.replace('/profile');
    }
  }, [router, status]);

  const handleLogin = async () => {
    setIsLoading(true);

    await signIn('google', { redirectTo: '/profile' });
    setIsLoading(false);
  };

  return (
    <section className="auth-panel auth-card">
      <p className="assistant-brand auth-brand">SchemeSathi</p>
      <h1 className="auth-title">Find government schemes through conversation.</h1>
      <p className="auth-copy">Secure Google sign-in. Your profile helps the assistant reason about eligibility and stays private.</p>

      <div className="auth-action">
        <button type="button" className="google-button" onClick={handleLogin} disabled={isLoading}>
          <span aria-hidden="true">G</span>
          {isLoading ? 'Signing in...' : 'Get Started Today!'}
        </button>
      </div>

      <p className="auth-trust">Secure sign-in with Google</p>
    </section>
  );
}
