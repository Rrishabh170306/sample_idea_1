"use client";

import { useRouter } from 'next/navigation';
import * as React from 'react';
import { loadSession, saveSession } from './session';

export function ProfileForm() {
  const router = useRouter();
  const [form, setForm] = React.useState(() => loadSession());
  const [submitted, setSubmitted] = React.useState(false);

  React.useEffect(() => {
    if (!form.authenticated) {
      router.replace('/auth');
    }
  }, [form.authenticated, router]);

  const updateField = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    saveSession(form);
    setSubmitted(true);
    window.setTimeout(() => {
      router.push('/chat');
    }, 450);
  };

  return (
    <section className="profile-panel">
      <p className="eyebrow">Profile Setup</p>
      <h1 className="page-title">Complete your profile</h1>
      <p className="page-copy">
        We collect these details once so the chatbot can reason about eligibility consistently.
      </p>

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
          <button type="submit" className="primary-button" disabled={submitted}>
            {submitted ? 'Saving…' : 'Save profile and continue'}
          </button>
        </div>
      </form>
    </section>
  );
}
