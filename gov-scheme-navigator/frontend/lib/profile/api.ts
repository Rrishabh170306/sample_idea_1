import type { ProfileApiPayload, ProfileApiResponse, ProfileSaveResponse } from './types';

const DEFAULT_API_BASE_URL = 'http://localhost:8000';

function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL;
}

function buildHeaders(userEmail: string) {
  return {
    'Content-Type': 'application/json',
    'X-User-Email': userEmail,
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
  const response = await fetch(`${getApiBaseUrl()}/api/v1/profile/me`, {
    method: 'GET',
    headers: buildHeaders(userEmail),
    cache: 'no-store',
  });

  return parseResponse<ProfileApiResponse>(response);
}

export async function saveProfile(userEmail: string, profile: ProfileApiPayload): Promise<ProfileSaveResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/profile/me`, {
    method: 'PUT',
    headers: buildHeaders(userEmail),
    body: JSON.stringify(profile),
  });

  return parseResponse<ProfileSaveResponse>(response);
}
