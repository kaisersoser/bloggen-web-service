"use client"
import React, { useState, useEffect } from 'react';

interface TypewriterTextProps {
  text: string;
  speed?: number; // Characters per second
  className?: string;
  onComplete?: () => void;
}

export function TypewriterText({ 
  text, 
  speed = 40, // Set to 40 chars per second for dramatic streaming effect
  className = "",
  onComplete 
}: TypewriterTextProps) {
  const [displayedText, setDisplayedText] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    if (currentIndex < text.length && !isComplete) {
      const timeout = setTimeout(() => {
        setDisplayedText(prev => prev + text[currentIndex]);
        setCurrentIndex(prev => prev + 1);
      }, 1000 / speed);

      return () => clearTimeout(timeout);
    } else if (currentIndex >= text.length && !isComplete) {
      setIsComplete(true);
      onComplete?.();
    }
  }, [currentIndex, text, speed, isComplete, onComplete]);

  // Reset when text changes
  useEffect(() => {
    setDisplayedText('');
    setCurrentIndex(0);
    setIsComplete(false);
  }, [text]);

  return (
    <span className={className}>
      {displayedText}
      {!isComplete && (
        <span className="animate-pulse text-green-400 ml-1">▊</span>
      )}
    </span>
  );
}