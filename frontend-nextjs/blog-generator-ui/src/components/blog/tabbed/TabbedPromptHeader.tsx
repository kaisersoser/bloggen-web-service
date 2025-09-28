"use client";

import React from "react";
import { Brain, Lightbulb, Sparkles, Target, Zap } from "lucide-react";

interface TabbedPromptHeaderProps {
  remainingGenerations?: number;
  userRole?: "FREE" | "PREMIUM" | "ADMIN";
}

export function TabbedPromptHeader({ remainingGenerations, userRole = "FREE" }: TabbedPromptHeaderProps) {
  return (
    <div className="text-center mb-8 animate-soft-pop">
      <div className="inline-flex items-center gap-2 mb-4 px-4 py-2 rounded-full bg-gradient-to-r from-blue-500/15 via-purple-500/10 to-blue-500/15 transition-comfortable">
        <div className="p-2 rounded-lg bg-gradient-to-br from-blue-500 via-purple-500 to-indigo-500 animate-glow-pulse">
          <Sparkles className="w-6 h-6 text-white drop-shadow" />
        </div>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
          AI Blog Generator
        </h1>
      </div>

      <p className="text-gray-600 dark:text-gray-400 text-lg mb-4 transition-comfortable">
        Transform your ideas into engaging, well-researched blog posts with AI-powered content generation
      </p>

      <div className="flex items-center justify-center gap-6 text-sm">
        <div className="flex items-center gap-1 text-gray-600 dark:text-gray-400 transition-comfortable">
          <Brain className="w-4 h-4" />
          <span>AI-powered research</span>
        </div>
        <div className="flex items-center gap-1 text-gray-600 dark:text-gray-400 transition-comfortable">
          <Zap className="w-4 h-4" />
          <span>Real-time generation</span>
        </div>
        <div className="flex items-center gap-1 text-gray-600 dark:text-gray-400 transition-comfortable">
          <Lightbulb className="w-4 h-4" />
          <span>Creative content</span>
        </div>
        {remainingGenerations !== undefined && userRole !== "ADMIN" && (
          <div className="flex items-center gap-1 text-gray-600 dark:text-gray-400 transition-comfortable">
            <Target className="w-4 h-4" />
            <span>{remainingGenerations} generations remaining</span>
          </div>
        )}
      </div>
    </div>
  );
}
