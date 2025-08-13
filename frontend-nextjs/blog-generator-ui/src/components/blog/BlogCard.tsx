"use client"

import React, { useState, useEffect, useMemo, useCallback } from "react"

interface BlogData {
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

interface BlogCardProps {
  blog: BlogData
  onClick: (blog: BlogData) => void
  onDelete?: (blogId: string) => void
  variant?: "default" | "compact"
}

// Memoized function to generate AI summary of blog content
const generateSummary = (content: string | null): string => {
  if (!content) return "No content available"
  
  // Simple extractive summarization - take first meaningful sentence
  const cleanContent = content
    .replace(/#{1,6}\s+/g, '') // Remove markdown headers
    .replace(/\*\*/g, '') // Remove bold markdown
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // Convert links to text
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '') // Remove images
    .trim()
  
  if (cleanContent.length === 0) return "No content available"
  
  // Find first complete sentence or take first 20 words
  const sentences = cleanContent.split(/[.!?]+/)
  const firstSentence = sentences[0]?.trim()
  
  if (firstSentence && firstSentence.length <= 120) {
    return firstSentence + "."
  }
  
  // Fallback: take first 20 words
  const words = cleanContent.split(/\s+/).slice(0, 20)
  const summary = words.join(' ')
  
  return summary.length > 3 ? summary + "..." : "Blog content available"
}

// Memoized status helper functions
const getStatusColor = (status: string) => {
  switch (status.toUpperCase()) {
    case 'COMPLETED':
      return 'bg-green-100 text-green-800'
    case 'FAILED':
      return 'bg-red-100 text-red-800'
    case 'IN_PROGRESS':
      return 'bg-blue-100 text-blue-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

const getStatusLabel = (status: string) => {
  switch (status.toUpperCase()) {
    case 'COMPLETED':
      return 'Complete'
    case 'FAILED':
      return 'Failed'
    case 'IN_PROGRESS':
      return 'In Progress'
    default:
      return 'Queued'
  }
}

export const BlogCard = React.memo(function BlogCard({ blog, onClick, onDelete }: BlogCardProps) {
  const [summary, setSummary] = useState<string>("")
  
  // Memoize the summary generation to prevent recalculation on every render
  const memoizedSummary = useMemo(() => generateSummary(blog.content), [blog.content])
  
  useEffect(() => {
    setSummary(memoizedSummary)
  }, [memoizedSummary])
  
  // Memoize status styling to prevent recalculation
  const statusColorClass = useMemo(() => getStatusColor(blog.status), [blog.status])
  const statusLabel = useMemo(() => getStatusLabel(blog.status), [blog.status])
  
  // Memoize formatted date to prevent recalculation
  const formattedDate = useMemo(() => {
    return new Date(blog.createdAt).toLocaleDateString()
  }, [blog.createdAt])
  
  // Memoize card click handler to prevent recreation
  const handleCardClick = useCallback(() => {
    onClick(blog)
  }, [onClick, blog])
  
  // Memoize delete handler to prevent recreation
  const handleDeleteClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    if (onDelete) {
      onDelete(blog.id)
    }
  }, [onDelete, blog.id])
  
  // Memoize background style to prevent object recreation
  const backgroundStyle = useMemo(() => ({
    height: '280px',
    width: '100%',
    backgroundImage: blog.heroImageUrl ? `url(${blog.heroImageUrl})` : undefined,
    backgroundSize: 'cover' as const,
    backgroundPosition: 'center' as const,
    backgroundBlendMode: blog.heroImageUrl ? ('overlay' as const) : undefined
  }), [blog.heroImageUrl])
  
  return (
    <div
      className="group relative cursor-pointer transform transition-all duration-200 hover:scale-105 hover:shadow-lg"
    >
      <div
        className="relative overflow-hidden rounded-xl p-6 shadow-md border border-gray-100 hover:border-blue-200 bg-gradient-to-br from-blue-50 via-white to-purple-50"
        style={backgroundStyle}
        onClick={handleCardClick}
      >
        {/* Glossy overlay effect */}
        <div className="absolute inset-0 bg-gradient-to-br from-white/55 to-white/10 backdrop-blur-[2px] pointer-events-none"></div>
        
        {/* Delete Button - Top Right Corner */}
        {onDelete && (
          <button
            onClick={handleDeleteClick}
            className="absolute top-3 right-3 z-20 opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-red-500 hover:bg-red-600 text-white rounded-full p-2 shadow-lg"
            title="Delete blog forever"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          </button>
        )}
        
        {/* Topic - Top (Fixed height) */}
        <div className="relative z-10 mb-4 h-16">
          <h3 
            className="font-semibold text-gray-900 text-sm group-hover:text-blue-600 transition-colors overflow-hidden"
            style={{
              display: '-webkit-box',
              WebkitLineClamp: 3,
              WebkitBoxOrient: 'vertical',
              lineHeight: '1.3em',
              height: '3.9em' // 3 lines max
            }}
            title={blog.topic} // Show full title on hover
          >
            {blog.topic}
          </h3>
        </div>
        
        {/* Instructions - Small text (Fixed height) */}
        {blog.instructions && (
          <div className="relative z-10 mb-3 h-8">
            <p 
              className="text-xs text-gray-500 overflow-hidden"
              style={{
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                lineHeight: '1.2em',
                height: '2.4em'
              }}
              title={blog.instructions}
            >
              {blog.instructions}
            </p>
          </div>
        )}
        
        {/* AI-Generated Summary (Fixed height) */}
        <div className="relative z-10 mb-4 h-20">
          <p 
            className="text-xs text-gray-600 italic overflow-hidden"
            style={{
              display: '-webkit-box',
              WebkitLineClamp: 4,
              WebkitBoxOrient: 'vertical',
              lineHeight: '1.3em',
              height: '5.2em'
            }}
            title={summary}
          >
            {summary}
          </p>
        </div>
        
        {/* Footer - Status and Date (Fixed position at bottom) */}
        <div className="absolute bottom-6 left-6 right-6 z-10 flex items-center justify-between">
          <span className="text-xs text-gray-400">
            {formattedDate}
          </span>
          <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${statusColorClass}`}>
            {statusLabel}
          </span>
        </div>
        
        {/* Shimmer effect on hover */}
        <div className="absolute inset-0 -top-2 -left-2 bg-gradient-to-r from-transparent via-white/30 to-transparent transform -skew-x-12 opacity-0 group-hover:opacity-100 group-hover:animate-shimmer pointer-events-none"></div>
      </div>
    </div>
  )
}, (prevProps, nextProps) => {
  // Custom comparison function for optimal re-rendering
  return (
    prevProps.blog.id === nextProps.blog.id &&
    prevProps.blog.topic === nextProps.blog.topic &&
    prevProps.blog.content === nextProps.blog.content &&
    prevProps.blog.status === nextProps.blog.status &&
    prevProps.blog.heroImageUrl === nextProps.blog.heroImageUrl &&
    prevProps.blog.createdAt === nextProps.blog.createdAt &&
    prevProps.variant === nextProps.variant &&
    prevProps.onClick === nextProps.onClick &&
    prevProps.onDelete === nextProps.onDelete
  )
})
