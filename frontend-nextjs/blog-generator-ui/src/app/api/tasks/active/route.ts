// src/app/api/tasks/active/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { getFrontendUrl } from '@/config/protocol';
import { authenticatedBackendFetch } from '@/lib/backend-fetch';

export const runtime = 'nodejs'

export async function GET(request: NextRequest) {
  try {
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
    const response = await authenticatedBackendFetch('/tasks/active', token);

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Backend error:', errorText);
      return NextResponse.json({ error: 'Failed to fetch active tasks' }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Active tasks API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
