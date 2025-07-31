"use client"

import { useState, useEffect, useCallback } from 'react'

interface BlogData {
  id: string
  userId: string
  topic: string
  instructions: string | null
  content: string | null
  status: string
  progress: number
  currentStep: string | null
  error: string | null
  createdAt: Date
  updatedAt: Date
  completedAt: Date | null
}

interface UseInfiniteScrollProps {
  allBlogs: BlogData[]
  itemsPerPage?: number
}

export function useInfiniteScroll({ allBlogs, itemsPerPage = 6 }: UseInfiniteScrollProps) {
  const [displayedBlogs, setDisplayedBlogs] = useState<BlogData[]>([])
  const [hasMore, setHasMore] = useState(true)
  const [isLoading, setIsLoading] = useState(false)

  // Initialize with first batch
  useEffect(() => {
    if (allBlogs.length > 0) {
      const initialBlogs = allBlogs.slice(0, itemsPerPage)
      setDisplayedBlogs(initialBlogs)
      setHasMore(allBlogs.length > itemsPerPage)
    } else {
      setDisplayedBlogs([])
      setHasMore(false)
    }
  }, [allBlogs, itemsPerPage])

  const loadMore = useCallback(() => {
    if (isLoading || !hasMore) return

    setIsLoading(true)
    
    // Simulate slight delay for smooth UX
    setTimeout(() => {
      const currentLength = displayedBlogs.length
      const nextBlogs = allBlogs.slice(currentLength, currentLength + itemsPerPage)
      
      if (nextBlogs.length > 0) {
        setDisplayedBlogs(prev => [...prev, ...nextBlogs])
        setHasMore(currentLength + nextBlogs.length < allBlogs.length)
      } else {
        setHasMore(false)
      }
      
      setIsLoading(false)
    }, 300)
  }, [allBlogs, displayedBlogs.length, itemsPerPage, isLoading, hasMore])

  // Intersection Observer for infinite scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const target = entries[0]
        if (target.isIntersecting && hasMore && !isLoading) {
          loadMore()
        }
      },
      {
        threshold: 0.1,
        rootMargin: '100px' // Start loading 100px before the sentinel comes into view
      }
    )

    const sentinel = document.getElementById('blog-scroll-sentinel')
    if (sentinel) {
      observer.observe(sentinel)
    }

    return () => {
      if (sentinel) {
        observer.unobserve(sentinel)
      }
    }
  }, [hasMore, isLoading, loadMore])

  return {
    displayedBlogs,
    hasMore,
    isLoading,
    loadMore
  }
}
