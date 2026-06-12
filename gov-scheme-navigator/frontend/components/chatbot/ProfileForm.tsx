"use client";

import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import * as React from 'react';
import { loadProfileFromServer, saveProfileToServer } from '@/lib/profile/service';
import { loadSession, saveSession } from './session';

export function ProfileForm() {
  const router = useRouter();
  const { data: session, status } = useSession();
  const [form, setForm] = React.useState(() => loadSession());
  const [isLoading, setIsLoading] = React.useState(true);
  const [isSaving, setIsSaving] = React.useState(false);
  const [loadError, setLoadError] = React.useState<string | null>(null);
  const [saveError, setSaveError] = React.useState<string | null>(null);

  const userEmail = session?.user?.email ?? '';

  const updateField = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const hydrateProfile = React.useCallback(async () => {
    if (status === 'loading') {
      setIsLoading(true);
      return;
    }

    if (status !== 'authenticated' || !userEmail) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setLoadError(null);

    try {
      const serverProfile = await loadProfileFromServer(userEmail);
      setForm(serverProfile);
      saveSession(serverProfile);
    } catch {
      setForm(loadSession());
      setLoadError('Could not load your saved profile from the server. Using your local draft for now.');
    } finally {
      setIsLoading(false);
    }
  }, [status, userEmail]);

  React.useEffect(() => {
    void hydrateProfile();
  }, [hydrateProfile]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!userEmail) {
      setSaveError('You need to be signed in before saving your profile.');
      return;
    }

    setIsSaving(true);
    setSaveError(null);

    try {
      const savedProfile = await saveProfileToServer(userEmail, form);
      setForm(savedProfile);
      saveSession(savedProfile);
      router.push('/chat');
    } catch {
      saveSession(form);
      setSaveError('Could not save your profile to the server. Your latest draft is stored locally. Please retry.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <section className="profile-panel">
      <p className="eyebrow">Profile Setup</p>
      <h1 className="page-title">Complete your profile</h1>
      <p className="page-copy">
        We collect these details once so the chatbot can reason about eligibility consistently.
      </p>

      {session?.user?.email ? <p className="helper-text">Signed in as {session.user.email}</p> : null}
      {isLoading ? <p className="helper-text">Loading your saved profile...</p> : null}
      {loadError ? <p className="helper-text">{loadError}</p> : null}
      {loadError ? (
        <div className="action-row">
          <button type="button" className="btn" onClick={() => void hydrateProfile()}>
            Retry
          </button>
        </div>
      ) : null}
      {saveError ? <p className="helper-text">{saveError}</p> : null}

      <form onSubmit={handleSubmit} className="profile-form">
        <div className="form-grid">
          <label className="field-group">
            <span className="field-label">Full name</span>
            <input className="text-field" value={form.fullName} onChange={(e) => updateField('fullName', e.target.value)} />
          </label>
          <label className="field-group">
            <span className="field-label">Date of birth</span>
            <input className="text-field" type="date" value={form.dob} onChange={(e) => updateField('dob', e.target.value)} />
          </label>
          <label className="field-group full-width">
            <span className="field-label">Address</span>
            <input className="text-field" value={form.address} onChange={(e) => updateField('address', e.target.value)} />
          </label>
          <label className="field-group">
            <span className="field-label">City</span>
            <input className="text-field" value={form.city} onChange={(e) => updateField('city', e.target.value)} />
          </label>
          <label className="field-group">
            <span className="field-label">Pin code</span>
            <input className="text-field" value={form.pinCode} onChange={(e) => updateField('pinCode', e.target.value)} />
          </label>
          <label className="field-group">
            <span className="field-label">Annual income</span>
            <input className="text-field" value={form.income} onChange={(e) => updateField('income', e.target.value)} />
          </label>
          <label className="field-group">
            <span className="field-label">Background</span>
            <select className="text-field" value={form.background} onChange={(e) => updateField('background', e.target.value as 'rural' | 'urban' | '')}>
              <option value="">Select</option>
              <option value="rural">Rural</option>
              <option value="urban">Urban</option>
            </select>
          </label>
          <label className="field-group full-width">
            <span className="field-label">Education / background notes</span>
            <input className="text-field" value={form.educationBackground} onChange={(e) => updateField('educationBackground', e.target.value)} />
          </label>
        </div>

        <div className="action-row">
          <button type="submit" className="primary-button" disabled={isSaving || isLoading}>
            {isSaving ? 'Saving...' : 'Save profile and continue'}
          </button>
        </div>
      </form>
    </section>
  );
}
