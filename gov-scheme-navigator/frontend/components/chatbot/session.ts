import { createEmptyProfileValues } from '@/lib/profile/adapter';
import type { ProfileFormValues } from '@/lib/profile/types';

export type SchemeSathiSession = ProfileFormValues;

const STORAGE_KEY = 'schemesathi.session';

export function createEmptySession(): SchemeSathiSession {
  return createEmptyProfileValues();
}

export function loadSession(): SchemeSathiSession {
  if (typeof window === 'undefined') {
    return createEmptySession();
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return createEmptySession();
    }

    const parsed = JSON.parse(raw) as Partial<SchemeSathiSession>;
    return {
      ...createEmptySession(),
      ...parsed,
    };
  } catch {
    return createEmptySession();
  }
}

export function saveSession(session: SchemeSathiSession) {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function updateSession(patch: Partial<SchemeSathiSession>) {
  const current = loadSession();
  const next = { ...current, ...patch };
  saveSession(next);
  return next;
}

export function isProfileComplete(session: SchemeSathiSession) {
  return Boolean(
    session.fullName &&
      session.dob &&
      session.address &&
      session.city &&
      session.pinCode &&
      session.income &&
      session.background &&
      session.educationBackground,
  );
}
