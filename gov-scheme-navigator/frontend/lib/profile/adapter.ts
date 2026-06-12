import type { ProfileApiPayload, ProfileFormValues } from './types';

export function createEmptyProfileValues(): ProfileFormValues {
  return {
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

export function mapApiProfileToForm(profile: ProfileApiPayload | null | undefined): ProfileFormValues {
  if (!profile) {
    return createEmptyProfileValues();
  }

  return {
    fullName: profile.full_name ?? '',
    dob: profile.dob ?? '',
    address: profile.address ?? '',
    city: profile.city ?? '',
    pinCode: profile.pin_code ?? '',
    income: profile.income === null || profile.income === undefined ? '' : String(profile.income),
    background: profile.background ?? '',
    educationBackground: profile.education_background ?? '',
    language: profile.language ?? 'English',
    voiceEnabled: Boolean(profile.voice_enabled),
  };
}

export function mapFormToApiProfile(form: ProfileFormValues): ProfileApiPayload {
  const trimmedIncome = form.income.trim();

  return {
    full_name: form.fullName.trim(),
    dob: form.dob || null,
    address: form.address.trim(),
    city: form.city.trim(),
    pin_code: form.pinCode.trim(),
    income: trimmedIncome ? Number(trimmedIncome) : null,
    background: form.background || null,
    education_background: form.educationBackground.trim(),
    language: form.language,
    voice_enabled: form.voiceEnabled,
  };
}
