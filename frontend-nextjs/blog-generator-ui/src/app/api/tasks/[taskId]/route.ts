// src/app/api/tasks/[taskId]/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { getFrontendUrl } from '@/config/protocol';
import { authenticatedBackendFetch } from '@/lib/backend-fetch';

export const runtime = 'nodejs';

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ taskId: string }> }
) {
  try {
    const { taskId } = await params;
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

    // Forward request to FastAPI backend with SSL handling
    const response = await authenticatedBackendFetch(`/tasks/${taskId}`, token);

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json({ error: 'Task not found' }, { status: 404 });
      }
      const errorText = await response.text();
      console.error('Backend error:', errorText);
      return NextResponse.json({ error: 'Failed to fetch task status' }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Task status API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
