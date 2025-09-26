import { NextResponse } from 'next/server'
import { getServerSession } from "next-auth/next"
import { authOptions } from "@/lib/auth"
import { UserService } from "@/lib/services/user"
import { serverLogger } from '@/lib/logger/server'

export async function GET() {
  try {
    const session = await getServerSession(authOptions)
    
    if (!session || !session.user) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 })
    }

    // Get fresh user data from database
    const user = await UserService.getUserById(session.user.id)
    
    if (!user) {
      return NextResponse.json({ error: "User not found" }, { status: 404 })
    }

    // Define generation limits based on role
    let monthlyLimit: number
    switch (user.role) {
      case 'FREE':
        monthlyLimit = 50  // Updated for testing
        break
      case 'PREMIUM':
        monthlyLimit = -1  // Unlimited
        break
      case 'ADMIN':
        monthlyLimit = -1  // Unlimited
        break
      default:
        monthlyLimit = 50
    }

    // Check if we need to reset monthly count
    const now = new Date()
    const lastReset = new Date(user.lastGenerationReset)
    const isNewMonth = now.getMonth() !== lastReset.getMonth() || 
                      now.getFullYear() !== lastReset.getFullYear()

    const currentCount = isNewMonth ? 0 : user.monthlyGenerations
    const remainingGenerations = monthlyLimit === -1 ? -1 : Math.max(0, monthlyLimit - currentCount)

    return NextResponse.json({
      monthlyGenerations: currentCount,
      monthlyLimit: monthlyLimit,
      remainingGenerations: remainingGenerations,
      role: user.role,
      lastGenerationReset: user.lastGenerationReset
    })

  } catch (error) {
    serverLogger.error("Error fetching user stats", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}
