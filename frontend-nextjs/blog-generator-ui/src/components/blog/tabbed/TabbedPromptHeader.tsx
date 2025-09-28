"use client";

import React from "react";
import { Brain, Lightbulb, Sparkles, Target, Zap } from "lucide-react";

interface TabbedPromptHeaderProps {
  remainingGenerations?: number;
  userRole?: "FREE" | "PREMIUM" | "ADMIN";
}

export function TabbedPromptHeader({ remainingGenerations, userRole = "FREE" }: TabbedPromptHeaderProps) {
  return (
    <div className="text-center mb-8">
      <div className="inline-flex items-center gap-2 mb-4">
        <div className="p-2 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg">
          <Sparkles className="w-6 h-6 text-white" />
        </div>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
          AI Blog Generator
        </h1>
      </div>

      <p className="text-gray-600 dark:text-gray-400 text-lg mb-4">
        Transform your ideas into engaging, well-researched blog posts with AI-powered content generation
      </p>

      <div className="flex items-center justify-center gap-6 text-sm">
        <div className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
          <Brain className="w-4 h-4" />
          <span>AI-powered research</span>
        </div>
        <div className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
          <Zap className="w-4 h-4" />
          <span>Real-time generation</span>
        </div>
        <div className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
          <Lightbulb className="w-4 h-4" />
          <span>Creative content</span>
        </div>
        {remainingGenerations !== undefined && userRole !== "ADMIN" && (
          <div className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
            <Target className="w-4 h-4" />
            <span>{remainingGenerations} generations remaining</span>
          </div>
        )}
      </div>
    </div>
  );
}
