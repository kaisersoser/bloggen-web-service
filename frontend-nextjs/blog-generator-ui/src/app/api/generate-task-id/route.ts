import { NextRequest, NextResponse } from "next/server"
import { getServerSession } from "next-auth/next"
import { authOptions } from "@/lib/auth"
import { getToken } from "next-auth/jwt"
import http from 'http'
import https from 'https'
import jwt from 'jsonwebtoken'
import { isHttpsMode } from '@/config/protocol'

export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions)
    
    if (!session || !session.user) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 })
    }

    // Get JWT token for backend authentication
    const nextAuthToken = await getToken({ req: request, secret: process.env.NEXTAUTH_SECRET })
    
    // Create a JWT token that the backend expects
    const backendJWT = jwt.sign(
      {
        sub: session.user.id, // Subject (user ID)
        email: session.user.email,
        name: session.user.name,
        role: session.user.role || 'FREE',
        iat: Math.floor(Date.now() / 1000), // Issued at time
        exp: Math.floor(Date.now() / 1000) + (60 * 60) // Expires in 1 hour
      },
      process.env.NEXTAUTH_SECRET || 'fallback-secret',
      { algorithm: 'HS256' }
    )

    const backendUrl = isHttpsMode() ? 'https://localhost:5000' : 'http://localhost:5000'
    
    console.log(`🔗 Proxying generate-task-id request to backend: ${backendUrl}/generate-task-id`)

    return new Promise((resolve) => {
      const requestModule = isHttpsMode() ? https : http
      const requestOptions = {
        hostname: 'localhost',
        port: 5000,
        path: '/generate-task-id',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${backendJWT}`,
        },
        ...(isHttpsMode() && {
          rejectUnauthorized: false, // For self-signed certificates
        })
      }

      const backendRequest = requestModule.request(requestOptions, (backendResponse) => {
        let data = ''

        backendResponse.on('data', (chunk) => {
          data += chunk
        })

        backendResponse.on('end', () => {
          try {
            const responseData = JSON.parse(data)
            console.log(`✅ Generate-task-id response from backend:`, responseData)
            
            resolve(NextResponse.json(responseData, { status: backendResponse.statusCode || 200 }))
          } catch (error) {
            console.error('❌ Error parsing backend response:', error)
            resolve(NextResponse.json({ error: 'Invalid backend response' }, { status: 500 }))
          }
        })
      })

      backendRequest.on('error', (error) => {
        console.error('❌ Error connecting to backend for generate-task-id:', error)
        resolve(NextResponse.json({ error: 'Backend connection failed' }, { status: 500 }))
      })

      // No body data needed for task ID generation
      backendRequest.write(JSON.stringify({}))
      backendRequest.end()
    })

  } catch (error) {
    console.error('❌ Generate-task-id API error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}