import type { ProfileApiPayload, ProfileApiResponse, ProfileSaveResponse } from './types';

function buildHeaders() {
  return {
    'Content-Type': 'application/json',
  };
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function fetchProfile(userEmail: string): Promise<ProfileApiResponse> {
  const response = await fetch('/api/backend/profile/me', {
    method: 'GET',
    headers: buildHeaders(),
    cache: 'no-store',
  });

  return parseResponse<ProfileApiResponse>(response);
}

export async function saveProfile(userEmail: string, profile: ProfileApiPayload): Promise<ProfileSaveResponse> {
  const response = await fetch('/api/backend/profile/me', {
    method: 'PUT',
    headers: buildHeaders(),
    body: JSON.stringify(profile),
  });

  return parseResponse<ProfileSaveResponse>(response);
}
