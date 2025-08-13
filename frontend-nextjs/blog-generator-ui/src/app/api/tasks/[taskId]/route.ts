// src/app/api/tasks/[taskId]/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { API_BASE_URL } from '@/config/constants';
import https from 'https';

export const runtime = 'nodejs'

async function fetchWithTLSFallback(url: string, opts: any): Promise<Response> {
  return new Promise((resolve, reject) => {
    const urlObj = new URL(url);
    const isLocalhost = urlObj.hostname === 'localhost' || urlObj.hostname === '127.0.0.1';
    
    const options = {
      hostname: urlObj.hostname,
      port: urlObj.port || (urlObj.protocol === 'https:' ? 443 : 80),
      path: urlObj.pathname + urlObj.search,
      method: opts.method || 'GET',
      headers: opts.headers || {},
      // For localhost development, ignore SSL certificate issues
      rejectUnauthorized: !isLocalhost && process.env.NODE_ENV === 'production'
    };
    
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => {
        data += chunk;
      });
      res.on('end', () => {
        resolve({
          ok: (res.statusCode || 500) >= 200 && (res.statusCode || 500) < 300,
          status: res.statusCode || 500,
          statusText: res.statusMessage || '',
          json: () => Promise.resolve(JSON.parse(data)),
          text: () => Promise.resolve(data),
          headers: new Headers(res.headers as Record<string, string>)
        } as Response);
      });
    });
    
    req.on('error', (err) => {
      console.error('Request error:', err);
      reject(err);
    });
    
    // Write request body if provided
    if (opts.body) {
      req.write(opts.body);
    }
    
    req.end();
  });
}

interface RouteParams {
  params: {
    taskId: string;
  };
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const session = await getServerSession(authOptions);
    
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Get JWT token for backend authentication
    const frontendOrigin = `https://${request.headers.get('host')}`;
    
    const tokenResponse = await fetchWithTLSFallback(`${frontendOrigin}/api/auth/jwt-token`, {
      headers: {
        'Cookie': request.headers.get('cookie') || '',
      },
    });

    if (!tokenResponse.ok) {
      return NextResponse.json({ error: 'Authentication failed' }, { status: 401 });
    }

    const { token } = await tokenResponse.json();

    // Forward request to FastAPI backend with TLS fallback
    const response = await fetchWithTLSFallback(`${API_BASE_URL}/tasks/${params.taskId}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

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
