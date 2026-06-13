import { NextResponse } from 'next/server';
import { auth } from '@/auth';
import { buildBackendAuthHeaders, getBackendApiBaseUrl } from '@/lib/backend-auth';

export async function POST(request: Request) {
  const session = await auth();
  const email = session?.user?.email;

  if (!email) {
    return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 });
  }

  const body = await request.text();
  const response = await fetch(`${getBackendApiBaseUrl()}/api/v1/chat/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...buildBackendAuthHeaders(email),
    },
    body,
  });

  return new NextResponse(await response.text(), {
    status: response.status,
    headers: {
      'Content-Type': response.headers.get('Content-Type') || 'application/json',
    },
  });
}
