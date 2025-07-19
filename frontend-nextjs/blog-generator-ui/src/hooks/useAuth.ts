"use client"

import { useSession } from "next-auth/react"
import { useRouter } from "next/navigation"
import { useEffect } from "react"

export function useAuth(requireAuth = true) {
  const { data: session, status } = useSession()
  const router = useRouter()

  useEffect(() => {
    if (requireAuth && status === "loading") return // Still loading
    if (requireAuth && !session) {
      router.push("/auth/signin")
    }
  }, [session, status, requireAuth, router])

  return {
    session,
    status,
    isAuthenticated: !!session,
    isLoading: status === "loading",
    user: session?.user || null,
  }
}

export function useRoleCheck() {
  const { session } = useAuth()

  const hasRole = (role: string) => {
    return session?.user?.role === role
  }

  const canGenerateBlog = () => {
    if (!session) return false
    
    const user = session.user
    if (user.role === 'PREMIUM' || user.role === 'ADMIN') {
      return true
    }
    
    // Free users have a limit of 50 blogs per month (updated for testing)
    return user.monthlyGenerations < 50
  }

  const getRemainingGenerations = () => {
    if (!session) return 0
    
    const user = session.user
    if (user.role === 'PREMIUM' || user.role === 'ADMIN') {
      return Infinity
    }
    
    return Math.max(0, 50 - user.monthlyGenerations)
  }

  return {
    hasRole,
    canGenerateBlog,
    getRemainingGenerations,
    isFree: session?.user?.role === 'FREE',
    isPremium: session?.user?.role === 'PREMIUM',
    isAdmin: session?.user?.role === 'ADMIN',
  }
}
