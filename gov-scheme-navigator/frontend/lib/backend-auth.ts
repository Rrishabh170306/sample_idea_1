import crypto from 'crypto';

export function getBackendApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
}

export function buildBackendAuthHeaders(email: string) {
  const secret = process.env.AUTH_BACKEND_SHARED_SECRET || process.env.AUTH_SECRET;

  if (!secret) {
    throw new Error('Backend auth secret is not configured.');
  }

  const normalizedEmail = email.trim().toLowerCase();
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const signature = crypto.createHmac('sha256', secret).update(`${timestamp}.${normalizedEmail}`).digest('hex');

  return {
    'X-Auth-User-Email': normalizedEmail,
    'X-Auth-Timestamp': timestamp,
    'X-Auth-Signature': signature,
  };
}
