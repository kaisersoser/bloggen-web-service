import { NextRequest, NextResponse } from "next/server"
import { getServerSession } from "next-auth/next"
import { authOptions } from "@/lib/auth"
import https from 'https'
import fs from 'fs'
import path from 'path'
import jwt from 'jsonwebtoken'

// Force Node.js runtime (not Edge) so we can use custom https.Agent
export const runtime = 'nodejs'

async function fetchWithTLSFallback(url: string, opts: any) {
  // 1. Attempt with provided options (may include permissive agent)
  try {
    const res = await fetch(url, opts)
    if (res.ok) return res
    return res // propagate non-OK for caller handling
  } catch (err: any) {
    // 2. If certificate verification failed, retry with most permissive settings
    if (err?.code === 'UNABLE_TO_VERIFY_LEAF_SIGNATURE' || /certificate/i.test(String(err?.message))) {
      const insecureAgent = new https.Agent({ rejectUnauthorized: false })
      return await fetch(url, { ...opts, agent: insecureAgent })
    }
    throw err
  }
}

export async function POST(request: NextRequest) {
  let body: any = {};
  
  try {
    const session = await getServerSession(authOptions)
    
    if (!session || !session.user) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 })
    }

    // Create a JWT token that the backend expects
    const backendJWT = jwt.sign(
      {
        sub: session.user.id,
        email: session.user.email,
        name: session.user.name,
        role: session.user.role || 'FREE',
        iat: Math.floor(Date.now() / 1000),
        exp: Math.floor(Date.now() / 1000) + (60 * 60)
      },
      process.env.NEXTAUTH_SECRET!,
      { algorithm: 'HS256' }
    )

    body = await request.json()
    const { instructions } = body

    if (!instructions || typeof instructions !== 'string') {
      return NextResponse.json({ error: "Instructions are required" }, { status: 400 })
    }

    // Validate backend URL is configured
    if (!process.env.API_BASE_URL) {
      console.error('API_BASE_URL environment variable is not configured')
      return NextResponse.json({ error: "Backend configuration error" }, { status: 500 })
    }

    // Attempt to build a CA-backed agent if local certs available; fallback to permissive
    let httpsAgent: https.Agent | undefined
    try {
      const explicitCert = process.env.LOCAL_DEV_CERT && fs.existsSync(process.env.LOCAL_DEV_CERT)
      const certPathCandidates = [
        process.env.LOCAL_DEV_CERT || '',
        path.join(process.cwd(), 'certs', 'localhost.pem'),
        path.join(process.cwd(), '..', 'certs', 'localhost.pem')
      ].filter(p => p && fs.existsSync(p))
      if (explicitCert || certPathCandidates.length) {
        const certPath = explicitCert ? process.env.LOCAL_DEV_CERT! : certPathCandidates[0]
        const ca = fs.readFileSync(certPath)
        httpsAgent = new https.Agent({ ca, rejectUnauthorized: true })
      } else if (process.env.NODE_ENV !== 'production') {
        httpsAgent = new https.Agent({ rejectUnauthorized: false })
      }
    } catch (e) {
      console.warn('TLS agent setup failed; falling back to insecure dev agent:', e)
      if (process.env.NODE_ENV !== 'production') {
        httpsAgent = new https.Agent({ rejectUnauthorized: false })
      }
    }

    // Make request to backend
    const fetchOpts: any = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${backendJWT}`,
      },
      body: JSON.stringify({ instructions }),
    }
    if (httpsAgent) {
      fetchOpts.agent = httpsAgent
    }

    const backendUrl = `${process.env.API_BASE_URL}/generate-title`
    
    try {
      const backendResponse = await fetchWithTLSFallback(backendUrl, fetchOpts)

      if (!backendResponse.ok) {
        const errorText = await backendResponse.text()
        console.warn('Backend title generation failed:', errorText)
        // Fallback to simple title generation
        const fallbackTitle = instructions.length > 50 
          ? instructions.substring(0, 47) + '...'
          : instructions
        return NextResponse.json({ title: fallbackTitle })
      }

      const data = await backendResponse.json()
      return NextResponse.json(data)
      
    } catch (backendError) {
      console.warn('Backend title generation error:', backendError)
      // Fallback to simple title generation
      const fallbackTitle = instructions.length > 50 
        ? instructions.substring(0, 47) + '...'
        : instructions
      return NextResponse.json({ title: fallbackTitle })
    }

  } catch (error) {
    console.error('Title generation error:', error)
    // Final fallback - use instructions directly if available
    const fallbackTitle = body?.instructions?.length > 50 
      ? body.instructions.substring(0, 47) + '...'
      : body?.instructions || 'New Blog Post'
    return NextResponse.json({ title: fallbackTitle })
  }
}
