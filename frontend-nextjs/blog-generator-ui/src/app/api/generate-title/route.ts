import { NextRequest, NextResponse } from "next/server"
import { getServerSession } from "next-auth/next"
import { authOptions } from "@/lib/auth"
import jwt from 'jsonwebtoken'

// Force Node.js runtime (not Edge) for compatibility
export const runtime = 'nodejs'

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

    // Make request to backend (HTTP mode)
    const fetchOpts = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${backendJWT}`,
      },
      body: JSON.stringify({ instructions }),
    }

    const backendUrl = `${process.env.API_BASE_URL}/generate-title`
    
    try {
      const backendResponse = await fetch(backendUrl, fetchOpts)

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
