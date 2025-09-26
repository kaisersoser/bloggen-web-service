import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { BlogService } from '@/lib/services/user'
import { serverLogger } from '@/lib/logger/server'

export async function DELETE(request: NextRequest) {
  try {
    // Get the blog ID from the URL
    const url = new URL(request.url)
    const blogId = url.searchParams.get('id')
    
    if (!blogId) {
      return NextResponse.json(
        { error: 'Blog ID is required' },
        { status: 400 }
      )
    }

    // Check authentication
    const session = await getServerSession(authOptions)
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Authentication required' },
        { status: 401 }
      )
    }

    const userId = session.user.id

    // Get the blog to verify ownership
    const blog = await BlogService.getBlogById(blogId)
    
    if (!blog) {
      return NextResponse.json(
        { error: 'Blog not found' },
        { status: 404 }
      )
    }

    // Check if user owns the blog or is admin
    if (blog.userId !== userId && session.user.role !== 'ADMIN') {
      return NextResponse.json(
        { error: 'Permission denied' },
        { status: 403 }
      )
    }

    // Delete the blog
    await BlogService.deleteBlog(blogId)

    return NextResponse.json(
      { 
        message: 'Blog deleted successfully',
        deletedBlogId: blogId 
      },
      { status: 200 }
    )

  } catch (error) {
    serverLogger.error('Error deleting blog', error)
    return NextResponse.json(
      { error: 'Failed to delete blog' },
      { status: 500 }
    )
  }
}
