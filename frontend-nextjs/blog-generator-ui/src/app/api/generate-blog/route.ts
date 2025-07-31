import { NextRequest, NextResponse } from "next/server"
import { getServerSession } from "next-auth/next"
import { authOptions } from "@/lib/auth"
import { UserService, BlogService } from "@/lib/services/user"
import { getToken } from "next-auth/jwt"
import https from 'https'
import jwt from 'jsonwebtoken'

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
      process.env.NEXTAUTH_SECRET!,
      { algorithm: 'HS256' }
    )
    
    // With adapter disabled, use session data directly if token is not available
    if (!nextAuthToken && !session.user.id) {
      return NextResponse.json({ error: "Authentication token not found" }, { status: 401 })
    }

    const { topic, instructions } = await request.json()

    if (!topic || !topic.trim()) {
      return NextResponse.json({ error: "Topic is required" }, { status: 400 })
    }

    // Check if user can generate blogs
    const canGenerate = await UserService.canGenerateBlog(session.user.id)
    if (!canGenerate.allowed) {
      return NextResponse.json({ 
        error: "Generation limit reached",
        message: canGenerate.reason 
      }, { status: 403 })
    }

    // Create blog entry in database
    const blog = await BlogService.createBlog(
      session.user.id,
      topic.trim(),
      instructions?.trim()
    )

    // NOTE: Do NOT increment generation count here - only increment on successful completion
    // await UserService.incrementGenerationCount(session.user.id)

    // Forward request to Python backend with authentication
    // Use manual HTTPS request to handle self-signed certificates
    const backendUrl = new URL(`${process.env.API_BASE_URL}/generate-blog`)
    const postData = JSON.stringify({
      task_id: blog.id,
      topic: topic.trim(),
      instructions: instructions?.trim(),
      user_id: session.user.id
    })

    const backendResponse = await new Promise<{ok: boolean, status: number, json: () => Promise<{task_id?: string; error?: string}>, text: () => Promise<string>}>((resolve, reject) => {
      const options = {
        hostname: backendUrl.hostname,
        port: backendUrl.port || 5000,
        path: backendUrl.pathname,
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${backendJWT}`,
          'Content-Length': Buffer.byteLength(postData)
        },
        // Ignore SSL certificate issues in development
        rejectUnauthorized: process.env.NODE_ENV === 'production'
      }

      const req = https.request(options, (res) => {
        let data = ''
        res.on('data', (chunk) => {
          data += chunk
        })
        res.on('end', () => {
          try {
            const jsonData = JSON.parse(data)
            resolve({
              ok: (res.statusCode || 500) >= 200 && (res.statusCode || 500) < 300,
              status: res.statusCode || 500,
              json: () => Promise.resolve(jsonData),
              text: () => Promise.resolve(data)
            })
          } catch {
            resolve({
              ok: (res.statusCode || 500) >= 200 && (res.statusCode || 500) < 300,
              status: res.statusCode || 500,
              json: () => Promise.resolve({}),
              text: () => Promise.resolve(data)
            })
          }
        })
      })

      req.on('error', (error) => {
        reject(error)
      })

      req.write(postData)
      req.end()
    })

    if (!backendResponse.ok) {
      // Log the actual backend error for debugging
      let backendError = "Unknown error"
      try {
        const errorData = await backendResponse.json()
        backendError = JSON.stringify(errorData)
        console.error("Backend error response:", errorData)
      } catch {
        // If JSON parsing fails, get text response
        try {
          backendError = await backendResponse.text()
          console.error("Backend error text:", backendError)
        } catch {
          console.error("Could not parse backend error response")
        }
      }
      
      // Update blog status to failed
      await BlogService.updateBlogStatus(blog.id, 'FAILED', 0, `Backend error: ${backendError}`)
      throw new Error(`Backend returned error (${backendResponse.status}): ${backendError}`)
    }

    // Backend request successful
    return NextResponse.json({
      task_id: blog.id,
      message: "Blog generation started",
      blog_id: blog.id
    })

  } catch (error) {
    console.error("Error in blog generation:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}
