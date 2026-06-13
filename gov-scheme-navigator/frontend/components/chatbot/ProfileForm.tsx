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
    <section className="profile-panel onboarding-card">
      <div className="onboarding-intro">
        <p className="assistant-brand auth-brand">SchemeSathi</p>
        <h1 className="auth-title">Help us understand your situation.</h1>
        <p className="auth-copy">These details let the assistant match schemes, explain eligibility, and ask fewer follow-up questions later.</p>
      </div>

      <div className="onboarding-progress" aria-label="Profile onboarding progress">
        <span className="progress-step active">Personal</span>
        <span className="progress-step active">Location</span>
        <span className="progress-step active">Eligibility</span>
        <span className="progress-step">Review</span>
      </div>

      {session?.user?.email ? <p className="signed-in-note">Signed in as {session.user.email}</p> : null}
      {isLoading ? <p className="helper-text">Loading your saved profile...</p> : null}
      {loadError ? <p className="helper-text status-error inline-status">{loadError}</p> : null}
      {loadError ? (
        <div className="action-row">
          <button type="button" className="btn" onClick={() => void hydrateProfile()}>
            Retry
          </button>
        </div>
      ) : null}
      {saveError ? <p className="helper-text status-error inline-status">{saveError}</p> : null}

      <form onSubmit={handleSubmit} className="profile-form">
        <section className="onboarding-section">
          <div className="section-copy">
            <p className="section-kicker">Personal information</p>
            <h2>Who should the assistant reason for?</h2>
          </div>
          <div className="form-grid">
            <label className="field-group">
              <span className="field-label">Full name</span>
              <input className="text-field" value={form.fullName} onChange={(e) => updateField('fullName', e.target.value)} />
            </label>
            <label className="field-group">
              <span className="field-label">Date of birth</span>
              <input className="text-field date-field" type="date" value={form.dob} onChange={(e) => updateField('dob', e.target.value)} />
            </label>
          </div>
        </section>

        <section className="onboarding-section">
          <div className="section-copy">
            <p className="section-kicker">Location</p>
            <h2>Where should schemes be matched?</h2>
          </div>
          <div className="form-grid">
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
          </div>
        </section>

        <section className="onboarding-section">
          <div className="section-copy">
            <p className="section-kicker">Eligibility information</p>
            <h2>What context should the assistant consider?</h2>
          </div>
          <div className="form-grid">
            <label className="field-group">
              <span className="field-label">Annual income</span>
              <input className="text-field" value={form.income} onChange={(e) => updateField('income', e.target.value)} />
            </label>
            <label className="field-group">
              <span className="field-label">Rural / urban background</span>
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
        </section>

        <div className="onboarding-submit">
          <p>Review your details, then continue into the chatbot. You can enrich this profile later through documents and conversation.</p>
          <button type="submit" className="google-button continue-button" disabled={isSaving || isLoading}>
            {isSaving ? 'Saving...' : 'Save profile and continue'}
          </button>
        </div>
      </form>
    </section>
  );
}
