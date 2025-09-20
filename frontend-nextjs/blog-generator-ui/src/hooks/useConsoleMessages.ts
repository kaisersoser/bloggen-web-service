import { useState, useCallback, useRef } from 'react';

export interface ConsoleMessage {
  id: string;
  timestamp: string;
  type: string;
  message: string;
  rawData?: any;
  level: 'info' | 'success' | 'warning' | 'error';
}

export function useConsoleMessages() {
  const [messages, setMessages] = useState<ConsoleMessage[]>([]);
  const messageCountRef = useRef(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const consoleContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive (within console container only)
  const scrollToBottom = useCallback(() => {
    if (consoleContainerRef.current && messagesEndRef.current) {
      // Scroll within the console container, not the entire page
      consoleContainerRef.current.scrollTo({
        top: consoleContainerRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, []);

  // Add a new console message
  const addMessage = useCallback((
    type: string,
    message: string,
    rawData?: any,
    level: ConsoleMessage['level'] = 'info'
  ) => {
    const newMessage: ConsoleMessage = {
      id: `msg-${Date.now()}-${++messageCountRef.current}`,
      timestamp: new Date().toISOString(),
      type,
      message,
      rawData,
      level
    };

    setMessages(prev => [...prev, newMessage]);
    
    // Auto-scroll after a short delay to ensure DOM is updated
    setTimeout(scrollToBottom, 100);
  }, [scrollToBottom]);

  // Clear all messages
  const clearMessages = useCallback(() => {
    setMessages([]);
    messageCountRef.current = 0;
  }, []);

  // Process SSE data into console message
  const processSSEData = useCallback((data: any): { type: string; message: string; rawData?: any } | null => {
    // Handle different SSE data formats
    if (typeof data === 'string') {
      try {
        const parsed = JSON.parse(data);
        return processSSEData(parsed);
      } catch {
        return { type: 'raw', message: data, rawData: data };
      }
    }

    // Handle structured data
    if (data && typeof data === 'object') {
      const messageType = data.event || data.type || 'message';
      
      let message = '';
      if (data.message) {
        message = data.message;
      } else if (data.data) {
        message = typeof data.data === 'string' ? data.data : JSON.stringify(data.data);
      } else {
        message = JSON.stringify(data);
      }

      return {
        type: messageType,
        message,
        rawData: data
      };
    }

    return null;
  }, []);

  // Format timestamp for display
  const formatTimestamp = useCallback((timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  }, []);

  // Get message type icon
  const getMessageIcon = useCallback((type: string, level: ConsoleMessage['level']) => {
    switch (level) {
      case 'success':
        return '✅';
      case 'warning':
        return '⚠️';
      case 'error':
        return '❌';
      default:
        switch (type) {
          case 'connected':
            return '🔗';
          case 'taskcreated':
            return '🆔';
          case 'initializing':
            return '⚡';
          case 'agentthinking':
            return '🤔';
          case 'toolcall':
            return '🛠️';
          case 'researchfinding':
            return '🔍';
          case 'contentstream':
            return '✍️';
          case 'status':
            return '📊';
          case 'completion':
          case 'completed':
            return '🎉';
          default:
            return '▶';
        }
    }
  }, []);

  // Get message color class
  const getMessageColorClass = useCallback((level: ConsoleMessage['level']) => {
    switch (level) {
      case 'success':
        return 'text-green-400';
      case 'warning':
        return 'text-yellow-400';
      case 'error':
        return 'text-red-400';
      default:
        return 'text-gray-300';
    }
  }, []);

  return {
    messages,
    addMessage,
    clearMessages,
    processSSEData,
    formatTimestamp,
    getMessageIcon,
    getMessageColorClass,
    messagesEndRef,
    consoleContainerRef,
    scrollToBottom
  };
}