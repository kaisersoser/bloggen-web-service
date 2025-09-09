"use client"
import React, { useState } from 'react';
import Image from 'next/image';
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { 
  Eye, 
  Trash2, 
  ExternalLink,
  Calendar,
  Sparkles,
  CheckCircle,
  AlertCircle,
  Loader2
} from "lucide-react";
import { formatDistanceToNow } from 'date-fns';

// Helper function to calculate word count from content
const getWordCount = (content: string | null | undefined): number => {
  if (!content) return 0;
  return content.trim().split(/\s+/).filter(word => word.length > 0).length;
};

interface BlogTileProps {
  blog: {
    id: string;
    topic?: string;
    instructions?: string | null;
    heroImageUrl?: string | null;
    createdAt?: string;
    status?: 'completed' | 'generating' | 'error';
    progress?: number;
    content?: string | null;
  };
  onView: (blog: any) => void;
  onDelete: (blog: any) => void;
  isSelectionMode?: boolean;
  isSelected?: boolean;
  isPulsing?: boolean;
  onSelectionToggle?: (blogId: string) => void;
  onLongPress?: (blogId: string) => void;
  onMouseUp?: () => void;
  className?: string;
}

export function BlogTile({ 
  blog, 
  onView, 
  onDelete, 
  isSelectionMode = false,
  isSelected = false,
  isPulsing = false,
  onSelectionToggle,
  onLongPress,
  onMouseUp,
  className = "" 
}: BlogTileProps) {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  
  // Calculate word count from content
  const wordCount = getWordCount(blog.content);

  // Selection event handlers
  const handleMouseDown = () => {
    if (!isSelectionMode && onLongPress) {
      onLongPress(blog.id);
    }
  };

  const handleMouseUp = () => {
    if (onMouseUp) {
      onMouseUp();
    }
  };

  const handleClick = () => {
    if (isSelectionMode && onSelectionToggle) {
      onSelectionToggle(blog.id);
    } else {
      onView(blog);
    }
  };

  const getStatusIcon = () => {
    switch (blog.status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'generating':
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <CheckCircle className="w-4 h-4 text-green-500" />;
    }
  };

  const getStatusText = () => {
    switch (blog.status) {
      case 'completed':
        return 'Published';
      case 'generating':
        return 'Generating...';
      case 'error':
        return 'Failed';
      default:
        return 'Published';
    }
  };

  const handleImageLoad = () => {
    setImageLoaded(true);
  };

  const handleImageError = () => {
    setImageError(true);
    setImageLoaded(true);
  };

  return (
    <Card 
      className={`group overflow-hidden transition-all duration-300 hover:shadow-xl hover:scale-[1.02] cursor-pointer bg-white dark:bg-gray-900 relative
        ${isSelectionMode ? 'border-dashed border-2 border-blue-300 dark:border-blue-600' : 'border border-gray-200 dark:border-gray-700'} 
        ${isSelected ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 border-solid' : ''}
        ${isPulsing ? 'animate-pulse border-blue-400' : ''}
        ${className}
      `}
      onClick={handleClick}
      onMouseDown={handleMouseDown}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      <div className="relative">
        {/* Selection checkbox - positioned absolutely in top-left */}
        {isSelectionMode && (
          <div className="absolute top-2 left-2 z-10">
            <input
              type="checkbox"
              checked={isSelected}
              onChange={() => onSelectionToggle && onSelectionToggle(blog.id)}
              onClick={(e) => e.stopPropagation()}
              className="w-5 h-5 text-blue-600 bg-white border-2 border-gray-300 rounded focus:ring-blue-500 focus:ring-2 cursor-pointer"
            />
          </div>
        )}

        {/* Hero Image Section */}
        <div className="aspect-[16/10] relative overflow-hidden bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-800 dark:to-gray-700">
          {blog.heroImageUrl && !imageError ? (
            <>
              {!imageLoaded && (
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                </div>
              )}
              {/* Use regular img tag for OpenAI DALL-E images to avoid Next.js optimization issues */}
              {blog.heroImageUrl.includes('oaidalleapiprodscus.blob.core.windows.net') ? (
                <img
                  src={blog.heroImageUrl}
                  alt={blog.topic || 'Blog post image'}
                  className={`w-full h-full object-cover transition-opacity duration-300 ${
                    imageLoaded ? 'opacity-100' : 'opacity-0'
                  }`}
                  onLoad={handleImageLoad}
                  onError={handleImageError}
                />
              ) : (
                <Image
                  src={blog.heroImageUrl}
                  alt={blog.topic || 'Blog post image'}
                  fill
                  className={`object-cover transition-opacity duration-300 ${
                    imageLoaded ? 'opacity-100' : 'opacity-0'
                  }`}
                  onLoad={handleImageLoad}
                  onError={handleImageError}
                  sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 25vw"
                />
              )}
            </>
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <div className="text-center text-gray-400 dark:text-gray-500">
                <Sparkles className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p className="text-sm font-medium">AI Generated</p>
              </div>
            </div>
          )}

          {/* Status Badge */}
          <div className="absolute top-3 right-3">
            <div className={`
              flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium 
              backdrop-blur-sm border
              ${blog.status === 'completed' 
                ? 'bg-green-50/80 text-green-700 border-green-200' 
                : blog.status === 'generating'
                ? 'bg-blue-50/80 text-blue-700 border-blue-200'
                : 'bg-red-50/80 text-red-700 border-red-200'
              }
            `}>
              {getStatusIcon()}
              {getStatusText()}
            </div>
          </div>

          {/* Hover Overlay - only show when not in selection mode */}
          {!isSelectionMode && (
            <div className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center">
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  className="bg-white/90 hover:bg-white text-gray-900 backdrop-blur-sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    onView(blog);
                  }}
                >
                  <Eye className="w-4 h-4 mr-1" />
                  View
                </Button>
                <Button
                  size="sm"
                  variant="destructive"
                  className="bg-red-500/90 hover:bg-red-600 text-white backdrop-blur-sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(blog);
                  }}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Content Section */}
        <div className="p-4">
          {/* Title */}
          <h3 className="font-semibold text-lg text-gray-900 dark:text-white line-clamp-2 mb-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
            {blog.topic || 'Untitled Blog'}
          </h3>

          {/* Instructions Tag (if available) */}
          {blog.instructions && (
            <div className="mb-3">
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                Custom Instructions
              </span>
            </div>
          )}

          {/* Metadata */}
          <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" />
                <span>{formatDistanceToNow(new Date(blog.createdAt || Date.now()), { addSuffix: true })}</span>
              </div>
              {wordCount > 0 && (
                <div className="flex items-center gap-1">
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span>{wordCount.toLocaleString()} words</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
