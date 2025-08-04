import { NextRequest, NextResponse } from "next/server"
import { getServerSession } from "next-auth/next"
import { authOptions } from "@/lib/auth"
import https from 'https'
import jwt from 'jsonwebtoken'

export async function POST(request: NextRequest) {
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

    const body = await request.json()
    const { instructions } = body

    if (!instructions || typeof instructions !== 'string') {
      return NextResponse.json({ error: "Instructions are required" }, { status: 400 })
    }

    // Validate backend URL is configured
    if (!process.env.API_BASE_URL) {
      console.error('API_BASE_URL environment variable is not configured')
      return NextResponse.json({ error: "Backend configuration error" }, { status: 500 })
    }

    // Configure HTTPS agent to ignore self-signed certificates for local development
    const httpsAgent = new https.Agent({
      rejectUnauthorized: false
    })

    // Make request to backend
    const backendResponse = await fetch(`${process.env.API_BASE_URL}/generate-title`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${backendJWT}`,
      },
      body: JSON.stringify({ instructions }),
      // @ts-expect-error - agent is valid for node.js fetch
      agent: httpsAgent,
    })

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text()
      console.error('Backend error:', errorText)
      return NextResponse.json(
        { error: 'Failed to generate title' },
        { status: backendResponse.status }
      )
    }

    const data = await backendResponse.json()
    return NextResponse.json(data)

  } catch (error) {
    console.error('Title generation error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
