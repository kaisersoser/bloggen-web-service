"use client"
import React, { useState, useEffect, useRef } from 'react';

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
  const indexRef = useRef(0);

  useEffect(() => {
    if (text.length === 0 || isComplete) {
      return;
    }

  const effectiveSpeed = Math.max(speed, 1);
  const charsPerMillisecond = effectiveSpeed / 1000;
    let animationFrame: number | null = null;
    let lastTimestamp = 0;
    let accumulator = 0;

    const step = (timestamp: number) => {
      if (lastTimestamp === 0) {
        lastTimestamp = timestamp;
      }

      accumulator += timestamp - lastTimestamp;
      lastTimestamp = timestamp;

      const projectedAdvance = accumulator * charsPerMillisecond;

      if (projectedAdvance >= 1) {
        const charactersToAdvance = Math.floor(projectedAdvance);
        accumulator -= charactersToAdvance / charsPerMillisecond;
        indexRef.current = Math.min(indexRef.current + charactersToAdvance, text.length);
        setCurrentIndex(indexRef.current);
        setDisplayedText(text.slice(0, indexRef.current));

        if (indexRef.current >= text.length) {
          setIsComplete(true);
          onComplete?.();
          return;
        }
      }

      animationFrame = requestAnimationFrame(step);
    };

    animationFrame = requestAnimationFrame(step);

    return () => {
      if (animationFrame) {
        cancelAnimationFrame(animationFrame);
      }
    };
  }, [isComplete, onComplete, speed, text]);

  // Reset when text changes
  useEffect(() => {
    setDisplayedText('');
    setCurrentIndex(0);
    setIsComplete(false);
    indexRef.current = 0;
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