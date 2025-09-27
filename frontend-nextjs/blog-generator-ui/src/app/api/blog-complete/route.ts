import { NextRequest, NextResponse } from "next/server"
import { getServerSession } from "next-auth/next"
import { authOptions } from "@/lib/auth"
import { BlogService } from "@/lib/services/user"
import { serverLogger } from "@/lib/logger/server"
import { VERBOSE_LOGGING_ENABLED } from '@/lib/logger/env'

export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions)
    
    if (!session || !session.user) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 })
    }

    const { blog_id, status, content, error, hero_image_url } = await request.json()

    if (VERBOSE_LOGGING_ENABLED) {
      serverLogger.info('Blog completion request received', {
        blogId: blog_id,
        status,
        contentLength: content?.length || 0,
        error,
        heroImageUrl: hero_image_url,
      })
    }

    if (!blog_id) {
      return NextResponse.json({ error: "Blog ID is required" }, { status: 400 })
    }

    // Update blog status in database
    if (status === 'completed' && content) {
  await BlogService.updateBlogStatus(blog_id, 'COMPLETED', 100, 'Blog generation complete', content, undefined, hero_image_url || undefined)
      
      // Generation count is incremented automatically in updateBlogStatus
      return NextResponse.json({ 
        message: "Blog completed successfully",
        credit_deducted: true
      })
    } else if (status === 'failed') {
      await BlogService.updateBlogStatus(blog_id, 'FAILED', 0, error?.user_message || 'Generation failed')
      
      // Do NOT increment generation count on failure
      return NextResponse.json({ 
        message: "Blog generation failed",
        credit_deducted: false
      })
    }

    return NextResponse.json({ error: "Invalid status" }, { status: 400 })

  } catch (error) {
    serverLogger.error('Error updating blog completion', { error })
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}
