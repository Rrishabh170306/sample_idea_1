export type SchemeSathiSession = {
  authenticated: boolean;
  email: string;
  fullName: string;
  dob: string;
  address: string;
  city: string;
  pinCode: string;
  income: string;
  background: 'rural' | 'urban' | '';
  educationBackground: string;
  language: string;
  voiceEnabled: boolean;
};

const STORAGE_KEY = 'schemesathi.session';

export function createEmptySession(): SchemeSathiSession {
  return {
    authenticated: false,
    email: '',
    fullName: '',
    dob: '',
    address: '',
    city: '',
    pinCode: '',
    income: '',
    background: '',
    educationBackground: '',
    language: 'English',
    voiceEnabled: false,
  };
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
    session.authenticated &&
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
