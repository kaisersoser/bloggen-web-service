"use client"

import { useEffect } from 'react'
import { useSession } from 'next-auth/react'
import { useQuery, useQueryClient } from '@tanstack/react-query'

interface UserStats {
  monthlyGenerations: number
  monthlyLimit: number
  remainingGenerations: number
  role: string
  lastGenerationReset: string
}

export function useUserStats() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  const statsQuery = useQuery<UserStats>({
    queryKey: ['user-stats'],
    enabled: Boolean(session),
    queryFn: async () => {
      const response = await fetch('/api/user/stats', {
        credentials: 'include'
      })

      if (!response.ok) {
        throw new Error('Failed to fetch user stats')
      }

      return await response.json()
    },
    staleTime: 5 * 60 * 1000,
    retry: 1,
  })

  useEffect(() => {
    if (!session) {
      queryClient.removeQueries({ queryKey: ['user-stats'] })
    }
  }, [queryClient, session])

  const loading = statsQuery.isPending || (statsQuery.isFetching && !statsQuery.data)
  const errorMessage = statsQuery.error instanceof Error ? statsQuery.error.message : null

  return {
    stats: statsQuery.data ?? null,
    loading,
    error: errorMessage,
    refetch: statsQuery.refetch
  }
}
