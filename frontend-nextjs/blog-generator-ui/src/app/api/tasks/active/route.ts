// src/app/api/tasks/active/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { getFrontendUrl } from '@/config/protocol';
import { authenticatedBackendFetch } from '@/lib/backend-fetch';
import { serverLogger } from '@/lib/logger/server';

export const runtime = 'nodejs'

export async function GET(request: NextRequest) {
  try {
    // Debug: Check environment variables
    serverLogger.info('Active tasks route environment', {
      nodeTlsRejectUnauthorized: process.env.NODE_TLS_REJECT_UNAUTHORIZED,
      apiBaseUrl: process.env.API_BASE_URL,
    });
    
    const session = await getServerSession(authOptions);
    
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Get JWT token for backend authentication
    const frontendOrigin = getFrontendUrl();
    
    const tokenResponse = await fetch(`${frontendOrigin}/api/auth/jwt-token`, {
      headers: {
        'Cookie': request.headers.get('cookie') || '',
      },
    });

    if (!tokenResponse.ok) {
      return NextResponse.json({ error: 'Authentication failed' }, { status: 401 });
    }

    const { token } = await tokenResponse.json();

    // Use utility function for backend fetch with SSL handling
    serverLogger.info('Calling authenticatedBackendFetch for active tasks', {
      tokenPresent: Boolean(token),
    });
    const response = await authenticatedBackendFetch('/tasks/active', token);

    if (!response.ok) {
      const errorText = await response.text();
      serverLogger.error('Backend error fetching active tasks', { errorText });
      return NextResponse.json({ error: 'Failed to fetch active tasks' }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    serverLogger.error('Active tasks API error details', {
      message: error instanceof Error ? error.message : String(error),
      code: error instanceof Error && 'code' in error ? error.code : undefined,
      cause: error instanceof Error && 'cause' in error ? error.cause : undefined,
      stack: error instanceof Error ? error.stack : undefined,
      errorType: typeof error,
      error: error
    });
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
