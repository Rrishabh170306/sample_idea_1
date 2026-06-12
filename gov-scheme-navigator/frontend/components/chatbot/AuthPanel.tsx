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
    <section className="auth-panel">
      <p className="eyebrow">Google login</p>
      <h1 className="page-title">Continue with Google</h1>
      <p className="page-copy">
        Sign in with your Google account to continue to profile onboarding.
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
