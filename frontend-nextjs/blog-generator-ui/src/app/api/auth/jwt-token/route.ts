import { NextResponse } from 'next/server'
import { getServerSession } from "next-auth/next"
import { authOptions } from "@/lib/auth"
import { serverLogger } from '@/lib/logger/server'
import jwt from 'jsonwebtoken'

export async function GET() {
  try {
    const session = await getServerSession(authOptions)
    
    if (!session || !session.user) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 })
    }

    // Create a JWT token that the backend SSE endpoint expects
    const token = jwt.sign(
      {
        sub: session.user.id, // Subject (user ID)
        email: session.user.email,
        name: session.user.name,
        role: session.user.role || 'FREE',
        iat: Math.floor(Date.now() / 1000), // Issued at time
        exp: Math.floor(Date.now() / 1000) + (60 * 60) // Expires in 1 hour
      },
      process.env.NEXTAUTH_SECRET!,
      { algorithm: 'HS256' }
    )

    return NextResponse.json({ token }, { status: 200 })
    
  } catch (error) {
    serverLogger.error("JWT token generation error", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}
