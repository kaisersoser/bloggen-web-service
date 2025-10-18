import { prisma } from "@/lib/prisma"
import { UserRole, BlogStatus } from "@prisma/client"
import { serverLogger } from "@/lib/logger/server"
import { VERBOSE_LOGGING_ENABLED } from '@/lib/logger/env'

// Re-export UserRole for convenience
export { UserRole, BlogStatus }

export interface UserData {
  id: string
  email: string | null  // Allow null to match Prisma schema
  name: string | null
  image: string | null
  role: UserRole
  monthlyGenerations: number
  lastGenerationReset: Date
  createdAt: Date
  updatedAt: Date
}

export interface BlogData {
  id: string
  userId: string
  topic: string
  instructions: string | null
  content: string | null
  heroImageUrl?: string | null
  status: string
  progress: number
  currentStep: string | null
  error: string | null
  createdAt: Date
  updatedAt: Date
  completedAt: Date | null
}

export class UserService {
  static async getUserById(id: string): Promise<UserData | null> {
    return await prisma.user.findUnique({
      where: { id }
    })
  }

  static async getUserByEmail(email: string): Promise<UserData | null> {
    return await prisma.user.findUnique({
      where: { email }
    })
  }

  static async updateUserRole(userId: string, role: UserRole): Promise<UserData> {
    return await prisma.user.update({
      where: { id: userId },
      data: { role }
    })
  }

  static async incrementGenerationCount(userId: string): Promise<UserData> {
    const user = await prisma.user.findUnique({
      where: { id: userId }
    })

    if (!user) {
      throw new Error('User not found')
    }

    // Check if we need to reset monthly count
    const now = new Date()
    const lastReset = new Date(user.lastGenerationReset)
    const isNewMonth = now.getMonth() !== lastReset.getMonth() || 
                      now.getFullYear() !== lastReset.getFullYear()

    if (isNewMonth) {
      return await prisma.user.update({
        where: { id: userId },
        data: { 
          monthlyGenerations: 1,
          lastGenerationReset: now
        }
      })
    }

    return await prisma.user.update({
      where: { id: userId },
      data: { 
        monthlyGenerations: user.monthlyGenerations + 1
      }
    })
  }

  static async canGenerateBlog(userId: string): Promise<{ allowed: boolean; reason?: string }> {
    const user = await this.getUserById(userId)
    if (!user) {
      return { allowed: false, reason: 'User not found' }
    }

    // Check monthly limits based on role
    let monthlyLimit: number
    switch (user.role) {
      case 'FREE':
        monthlyLimit = 50  // Increased for testing
        break
      case 'PREMIUM':
        monthlyLimit = Infinity
        break
      case 'ADMIN':
        monthlyLimit = Infinity
        break
      default:
        monthlyLimit = 50  // Increased default for testing
    }

    // Check if we need to reset monthly count
    const now = new Date()
    const lastReset = new Date(user.lastGenerationReset)
    const isNewMonth = now.getMonth() !== lastReset.getMonth() || 
                      now.getFullYear() !== lastReset.getFullYear()

    const currentCount = isNewMonth ? 0 : user.monthlyGenerations

    if (currentCount >= monthlyLimit) {
      return { 
        allowed: false, 
        reason: `Monthly limit of ${monthlyLimit} generations reached. Upgrade to Premium for unlimited access.` 
      }
    }

    return { allowed: true }
  }
}

export class BlogService {
  // Runtime guard to ensure new column exists (best-effort; prefer proper Prisma migration)
  private static heroColumnChecked = false
  private static async ensureHeroImageColumn() {
    if (this.heroColumnChecked) return
    try {
      const rows: Array<{ column_name: string }> = await prisma.$queryRawUnsafe(
        "SELECT column_name FROM information_schema.columns WHERE table_name='blogs' AND column_name='hero_image_url'"
      )
      if (!rows || rows.length === 0) {
        if (process.env.ALLOW_AUTO_MIGRATION === 'true') {
          try {
            await prisma.$executeRawUnsafe('ALTER TABLE "blogs" ADD COLUMN "hero_image_url" TEXT;')
            // Verify
            const verify: Array<{ column_name: string }> = await prisma.$queryRawUnsafe(
              "SELECT column_name FROM information_schema.columns WHERE table_name='blogs' AND column_name='hero_image_url'"
            )
            if (!verify || verify.length === 0) {
              serverLogger.warn('[BlogService] Failed to auto-add hero_image_url column.')
            } else {
              if (VERBOSE_LOGGING_ENABLED) {
                serverLogger.info('[BlogService] Added missing hero_image_url column automatically.')
              }
            }
          } catch (e) {
            serverLogger.warn('[BlogService] Auto-migration for hero_image_url failed', { error: e })
          }
        } else {
          serverLogger.warn('[BlogService] hero_image_url column missing. Run: npx prisma migrate dev --name add-hero-image-url (or prisma db push).')
        }
      }
    } catch (err) {
      serverLogger.debug('[BlogService] Column existence check failed (non-fatal)', { error: err })
    } finally {
      this.heroColumnChecked = true
    }
  }
  static async createBlog(userId: string, topic: string, instructions?: string, taskId?: string): Promise<BlogData> {
  await this.ensureHeroImageColumn()
  
    // Require taskId since we removed @default(cuid()) from schema
    if (!taskId) {
      throw new Error('taskId is required for blog creation')
    }
    
    return await prisma.blog.create({
      data: {
        id: taskId, // Use task_id as the blog ID
        userId,
        topic,
        instructions,
        heroImageUrl: null,
        status: 'QUEUED',
        progress: 0,
        currentStep: 'Starting...'
      }
    })
  }

  static async updateBlogStatus(
    blogId: string, 
    status: BlogStatus | string, 
    progress?: number, 
    currentStep?: string,
    content?: string,
  error?: string,
  heroImageUrl?: string
  ): Promise<BlogData> {
  await this.ensureHeroImageColumn()
    // Convert string status to BlogStatus enum if needed
    let blogStatus: BlogStatus
    if (typeof status === 'string') {
      // Map common string values to BlogStatus enum
      switch (status.toUpperCase()) {
        case 'QUEUED':
          blogStatus = BlogStatus.QUEUED
          break
        case 'IN_PROGRESS':
        case 'INPROGRESS':
          blogStatus = BlogStatus.IN_PROGRESS
          break
        case 'COMPLETED':
          blogStatus = BlogStatus.COMPLETED
          break
        case 'FAILED':
          blogStatus = BlogStatus.FAILED
          break
        default:
          throw new Error(`Invalid blog status: ${status}`)
      }
    } else {
      blogStatus = status
    }

    const updateData: { 
      status: BlogStatus
      progress?: number
      currentStep?: string
      content?: string
      error?: string
      completedAt?: Date
      heroImageUrl?: string | null
    } = { status: blogStatus }
    
    if (progress !== undefined) updateData.progress = progress
    if (currentStep !== undefined) updateData.currentStep = currentStep
    if (content !== undefined) updateData.content = content
    if (error !== undefined) updateData.error = error
  if (heroImageUrl !== undefined) updateData.heroImageUrl = heroImageUrl
    if (blogStatus === BlogStatus.COMPLETED) updateData.completedAt = new Date()

    const updatedBlog = await prisma.blog.update({
      where: { id: blogId },
      data: updateData
    })

    // Increment user's generation count when blog is successfully completed
    if (blogStatus === BlogStatus.COMPLETED) {
      await UserService.incrementGenerationCount(updatedBlog.userId)
    }

    return updatedBlog
  }

  static async getUserBlogs(userId: string): Promise<BlogData[]> {
  await this.ensureHeroImageColumn()
    return await prisma.blog.findMany({
      where: { userId },
      orderBy: { createdAt: 'desc' }
    })
  }

  static async getBlogById(blogId: string): Promise<BlogData | null> {
  await this.ensureHeroImageColumn()
    return await prisma.blog.findUnique({
      where: { id: blogId }
    })
  }

  static async deleteBlog(blogId: string): Promise<void> {
    await this.ensureHeroImageColumn()
    
    // Call backend API to handle both database deletion AND S3 cleanup
    // This ensures S3 images are properly cleaned up when blogs are deleted
    try {
      const { getBackendUrl } = await import('@/config/protocol')
      const backendUrl = getBackendUrl()
      
      // Get auth token using the same method as other services
      let token: string | null = null
      try {
        // Use fetch to get JWT token from our auth endpoint
        const tokenResponse = await fetch('/api/auth/jwt-token')
        if (tokenResponse.ok) {
          const tokenData = await tokenResponse.json()
          token = tokenData.token
        }
      } catch (tokenError) {
        serverLogger.warn('Could not get auth token for blog deletion', { error: tokenError })
      }
      
      // Call backend deletion endpoint (includes S3 cleanup)
      const response = await fetch(`${backendUrl}/tasks/${blogId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` })
        }
      })
      
      if (!response.ok) {
        // If backend deletion fails, fall back to direct database deletion
        // This ensures the UI doesn't break if backend is unavailable
        serverLogger.warn('Backend deletion failed, falling back to database deletion', {
          status: response.status,
        })
        await prisma.blog.delete({
          where: { id: blogId }
        })
        serverLogger.warn('Blog deleted from database only - S3 images may not be cleaned up')
        return
      }
      
      if (VERBOSE_LOGGING_ENABLED) {
        serverLogger.info('Blog deleted successfully with S3 cleanup', { blogId })
      }
      
    } catch (error) {
      serverLogger.error('Error calling backend deletion API', { error, blogId })
      
      // Fallback to direct database deletion if backend call fails
      serverLogger.warn('Falling back to direct database deletion', { blogId })
      await prisma.blog.delete({
        where: { id: blogId }
      })
      serverLogger.warn('Blog deleted from database only - S3 images may not be cleaned up', { blogId })
    }
  }
}
