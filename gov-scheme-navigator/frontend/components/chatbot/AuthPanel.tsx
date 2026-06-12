"use client";

import { useRouter } from 'next/navigation';
import * as React from 'react';
import { createEmptySession, saveSession } from './session';

export function AuthPanel() {
  const router = useRouter();
  const [isLoading, setIsLoading] = React.useState(false);

  const handleLogin = () => {
    setIsLoading(true);

    const nextSession = {
      ...createEmptySession(),
      authenticated: true,
      email: 'user@gmail.com',
    };

    saveSession(nextSession);

    window.setTimeout(() => {
      router.push('/profile');
    }, 450);
  };

  return (
    <section className="auth-panel">
      <p className="eyebrow">Google login</p>
      <h1 className="page-title">Continue with Google</h1>
      <p className="page-copy">
        This prototype routes you into profile onboarding after sign-in. The real Google account chooser requires a
        configured OAuth client and redirect URI.
      </p>

      <div className="action-row">
        <button type="button" className="primary-button" onClick={handleLogin} disabled={isLoading}>
          {isLoading ? 'Signing in…' : 'Continue with Google'}
        </button>
      </div>

      <p className="helper-text">After successful login, you will be redirected to profile onboarding.</p>
    </section>
  );
}
