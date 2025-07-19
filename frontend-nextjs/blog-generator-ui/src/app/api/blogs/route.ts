import { NextRequest, NextResponse } from "next/server"
import { getServerSession } from "next-auth/next"
import { authOptions } from "@/lib/auth"
import { BlogService } from "@/lib/services/user"

export async function GET(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions)
    
    if (!session || !session.user) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 })
    }

    const blogs = await BlogService.getUserBlogs(session.user.id)

    return NextResponse.json({ blogs })

  } catch (error) {
    console.error("Error fetching user blogs:", error)
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

    const success = await BlogService.deleteBlog(blogId, session.user.id)

    if (!success) {
      return NextResponse.json({ error: "Failed to delete blog" }, { status: 400 })
    }

    return NextResponse.json({ message: "Blog deleted successfully" })

  } catch (error) {
    console.error("Error deleting blog:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}
