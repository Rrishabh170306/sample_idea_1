import { NextResponse } from 'next/server';
import { auth } from '@/auth';
import { buildBackendAuthHeaders, getBackendApiBaseUrl } from '@/lib/backend-auth';

async function proxyProfileRequest(method: 'GET' | 'PUT', request?: Request) {
  const session = await auth();
  const email = session?.user?.email;

  if (!email) {
    return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 });
  }

  const response = await fetch(`${getBackendApiBaseUrl()}/api/v1/profile/me`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...buildBackendAuthHeaders(email),
    },
    body: method === 'PUT' && request ? await request.text() : undefined,
    cache: 'no-store',
  });

  return new NextResponse(await response.text(), {
    status: response.status,
    headers: {
      'Content-Type': response.headers.get('Content-Type') || 'application/json',
    },
  });
}

export async function GET() {
  return proxyProfileRequest('GET');
}

export async function PUT(request: Request) {
  return proxyProfileRequest('PUT', request);
}
