import { NextRequest, NextResponse } from "next/server"
import { getServerSession } from "next-auth/next"
import { authOptions } from "@/lib/auth"
import { UserService, BlogService } from "@/lib/services/user"
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
      process.env.NEXTAUTH_SECRET!,
      { algorithm: 'HS256' }
    )
    
    // With adapter disabled, use session data directly if token is not available
    if (!nextAuthToken && !session.user.id) {
      return NextResponse.json({ error: "Authentication token not found" }, { status: 401 })
    }

    const { topic, instructions, task_id } = await request.json()
    
    console.log('🆔 Generate-blog API received:', { topic: topic?.substring(0, 50), instructions: instructions?.substring(0, 50), task_id })

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
    console.log('Creating blog for user:', session.user.id, 'topic:', topic.trim())
    const blog = await BlogService.createBlog(
      session.user.id,
      topic.trim(),
      instructions?.trim()
    )
    console.log('Blog created successfully:', blog.id)

    // NOTE: Do NOT increment generation count here - only increment on successful completion
    // await UserService.incrementGenerationCount(session.user.id)

    // Handle long topic descriptions by auto-generating concise titles
    let finalTopic = topic.trim();
    const originalInstructions = instructions?.trim() || '';

    // If topic exceeds backend's 200-character limit, generate a concise title
    if (finalTopic.length > 200) {
      console.log(`Topic too long (${finalTopic.length} chars), generating concise title...`);
      
      try {
        // Use existing title generation API to create concise topic
        const titleResponse = await fetch(`${process.env.API_BASE_URL}/generate-title`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${backendJWT}`,
          },
          body: JSON.stringify({ instructions: finalTopic })
        });

        if (titleResponse.ok) {
          const titleData = await titleResponse.json();
          if (titleData.title && titleData.title.trim()) {
            finalTopic = titleData.title.trim();
            console.log(`Generated concise title: "${finalTopic}"`);
          } else {
            // Fallback: intelligent truncation
            finalTopic = finalTopic.substring(0, 197) + '...';
            console.log('Title generation returned empty, using truncated topic');
          }
        } else {
          // Fallback: intelligent truncation
          finalTopic = finalTopic.substring(0, 197) + '...';
          console.log('Title generation failed, using truncated topic');
        }
      } catch (error) {
        console.warn('Title generation error, using truncated topic:', error);
        // Fallback: intelligent truncation
        finalTopic = finalTopic.substring(0, 197) + '...';
      }
    }

    // Prepare instructions: use original long description if we generated a title
    const finalInstructions = finalTopic !== topic.trim() 
      ? topic.trim()  // Original long description becomes instructions
      : originalInstructions;  // Keep original instructions if topic was short

    // Forward request to Python backend with authentication
    // Use manual HTTP request to backend
    const backendUrl = new URL(`${process.env.API_BASE_URL}/generate-blog`)
    
    // SOLUTION 1: Use provided task_id if available, otherwise fall back to blog.id
    const finalTaskId = task_id || blog.id;
    console.log('🆔 Using task ID for backend:', finalTaskId, '(provided:', task_id, ', blog.id:', blog.id, ')');
    
    const postData = JSON.stringify({
      task_id: finalTaskId,
      topic: finalTopic,                    // Concise topic (≤200 chars)
      instructions: finalInstructions,      // Full original description or original instructions
      user_id: session.user.id
    })

    const backendResponse = await new Promise<{ok: boolean, status: number, json: () => Promise<{task_id?: string; error?: string}>, text: () => Promise<string>}>((resolve, reject) => {
      const options = {
        hostname: backendUrl.hostname,
        port: backendUrl.port || (isHttpsMode() ? 5000 : 5000),
        path: backendUrl.pathname,
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${backendJWT}`,
          'Content-Length': Buffer.byteLength(postData)
        },
        // Disable SSL verification for development self-signed certificates
        rejectUnauthorized: false
      }

      const httpModule = isHttpsMode() ? https : http;
      const req = httpModule.request(options, (res) => {
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
      task_id: finalTaskId,  // Return the actual task ID used
      message: "Blog generation started",
      blog_id: blog.id
    })

  } catch (error) {
    console.error("Error in blog generation:", error)
    console.error("Error details:", {
      message: error instanceof Error ? error.message : 'Unknown error',
      stack: error instanceof Error ? error.stack : 'No stack trace',
      type: typeof error,
      error: error
    })
    return NextResponse.json(
      { error: "Internal server error", details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
}
