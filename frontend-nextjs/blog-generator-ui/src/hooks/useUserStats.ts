"use client"

import { useState, useEffect, useCallback } from 'react'
import { useSession } from 'next-auth/react'

interface UserStats {
  monthlyGenerations: number
  monthlyLimit: number
  remainingGenerations: number
  role: string
  lastGenerationReset: string
}

export function useUserStats() {
  const { data: session } = useSession()
  const [stats, setStats] = useState<UserStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStats = useCallback(async () => {
    if (!session) {
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      const response = await fetch('/api/user/stats')
      
      if (!response.ok) {
        throw new Error('Failed to fetch user stats')
      }
      
      const data = await response.json()
      setStats(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch stats')
    } finally {
      setLoading(false)
    }
  }, [session])

  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  return {
    stats,
    loading,
    error,
    refetch: fetchStats
  }
}
