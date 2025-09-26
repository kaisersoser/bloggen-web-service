import { NextRequest, NextResponse } from "next/server"
import { getServerSession } from "next-auth/next"
import { authOptions } from "@/lib/auth"
import { BlogService } from "@/lib/services/user"
import { serverLogger } from '@/lib/logger/server'

export async function GET() {
  try {
    const session = await getServerSession(authOptions)
    
    if (!session || !session.user) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 })
    }

    const blogs = await BlogService.getUserBlogs(session.user.id)

    return NextResponse.json({ blogs })

  } catch (error) {
    serverLogger.error("Error fetching user blogs", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions)
    
    if (!session || !session.user) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const blogId = searchParams.get('id')

    if (!blogId) {
      return NextResponse.json({ error: "Blog ID is required" }, { status: 400 })
    }

    // Get the blog to verify ownership
    const blog = await BlogService.getBlogById(blogId)
    
    if (!blog) {
      return NextResponse.json({ error: "Blog not found" }, { status: 404 })
    }

    // Check if user owns the blog or is admin
    if (blog.userId !== session.user.id && session.user.role !== 'ADMIN') {
      return NextResponse.json({ error: "Permission denied" }, { status: 403 })
    }

    await BlogService.deleteBlog(blogId)

    return NextResponse.json({ message: "Blog deleted successfully" })

  } catch (error) {
    serverLogger.error("Error deleting blog", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}
