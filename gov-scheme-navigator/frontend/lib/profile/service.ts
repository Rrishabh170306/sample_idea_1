import { fetchProfile, saveProfile } from './api';
import { createEmptyProfileValues, mapApiProfileToForm, mapFormToApiProfile } from './adapter';
import type { ProfileFormValues } from './types';

export async function loadProfileFromServer(userEmail: string): Promise<ProfileFormValues> {
  const response = await fetchProfile(userEmail);
  return mapApiProfileToForm(response.profile);
}

export async function saveProfileToServer(userEmail: string, form: ProfileFormValues): Promise<ProfileFormValues> {
  const response = await saveProfile(userEmail, mapFormToApiProfile(form));
  return mapApiProfileToForm(response.profile);
}

export function getEmptyProfile(): ProfileFormValues {
  return createEmptyProfileValues();
}
