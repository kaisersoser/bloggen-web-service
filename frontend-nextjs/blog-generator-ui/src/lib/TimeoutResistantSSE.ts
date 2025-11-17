/**
 * Enhanced SSE implementation that bypasses browser EventSource limitations
 * Handles large AI content streaming with proper timeout and reconnection logic
 */

import { logger } from '@/lib/logger';
import { VERBOSE_LOGGING_ENABLED } from '@/lib/logger/env';

export interface SSEMessage {
  type: string;
  data: any;
  id?: string;
  retry?: number;
}

export interface SSEOptions {
  timeout?: number;
  retryDelay?: number;
  maxRetries?: number;
  reconnectOnError?: boolean;
  chunkSize?: number;
  maxRetryDelay?: number;
  backoffMultiplier?: number;
  jitterMs?: number;
}

type InternalSSEOptions = Required<Omit<SSEOptions, 'chunkSize'>> & {
  chunkSize: number;
};

export class TimeoutResistantSSE {
  private readonly urlFactory: () => Promise<string>;
  private currentUrl: string | null = null;
  private readonly options: InternalSSEOptions;
  private abortController: AbortController | null = null;
  private retryCount = 0;
  private lastEventId: string | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private isConnected = false;
  private isManuallyClosing = false;
  private isCompleted = false;
  private readonly listeners: Map<string, ((data: any) => void)[]> = new Map();
  private pendingOnlineListener: (() => void) | null = null;

  // Content chunking for large AI data
  private readonly contentBuffer: Map<string, {
    chunks: Map<number, string>;
    totalSize: number;
    received: number;
  }> = new Map();

  private canLogVerbose(): boolean {
    return VERBOSE_LOGGING_ENABLED && logger.shouldLog('info');
  }

  constructor(urlOrFactory: string | (() => Promise<string>), options: SSEOptions = {}) {
    this.urlFactory = typeof urlOrFactory === 'function'
      ? urlOrFactory
      : async () => urlOrFactory;

    this.options = {
      timeout: options.timeout ?? 900000, // 15 minutes (increased from 5 minutes)
      retryDelay: options.retryDelay ?? 1000,
      maxRetries: options.maxRetries ?? 5,
      reconnectOnError: options.reconnectOnError ?? true,
      chunkSize: options.chunkSize ?? 8192,
      maxRetryDelay: options.maxRetryDelay ?? 60000,
      backoffMultiplier: options.backoffMultiplier ?? 2,
      jitterMs: options.jitterMs ?? 500,
    };
  }

  /**
   * Start the SSE connection with enhanced error handling
   */
  async connect(): Promise<void> {
    if (this.isConnected) {
      logger.warn('SSE already connected or closed/completed', {
        isConnected: this.isConnected,
        isManuallyClosing: this.isManuallyClosing,
        isCompleted: this.isCompleted,
      });
      return;
    }

    if (this.isManuallyClosing) {
      this.isManuallyClosing = false;
    }

    if (this.isCompleted) {
      this.isCompleted = false;
    }

    this.clearOnlineListener();

    try {
      await this.establishConnection();
    } catch (error) {
      logger.error('SSE connection failed', { error, attempt: this.retryCount + 1 });

      if (
        this.options.reconnectOnError &&
        !this.isManuallyClosing &&
        !this.isCompleted &&
        this.retryCount < this.options.maxRetries
      ) {
        this.scheduleReconnect();
      } else {
        logger.warn('SSE connection terminated - max retries reached or task completed', {
          retryCount: this.retryCount,
          maxRetries: this.options.maxRetries,
          reconnectOnError: this.options.reconnectOnError,
        });
        this.emit('error', {
          message: 'Failed to establish SSE connection after maximum retries',
          retryCount: this.retryCount,
          originalError: error,
        });
      }
    }
  }

  /**
   * Establish the actual SSE connection using fetch
   */
  private async establishConnection(): Promise<void> {
    this.abortController = new AbortController();
    const url = await this.resolveUrl();

    const connectionTimeoutId = setTimeout(() => {
      logger.warn('Initial SSE connection timeout reached - aborting', { timeoutMs: 60000 });
      this.abortController?.abort();
    }, 60000);

    const streamTimeoutId = setTimeout(() => {
      logger.warn('SSE stream timeout reached - aborting', { timeoutMs: this.options.timeout });
      this.abortController?.abort();
    }, this.options.timeout);

    try {
      if (this.canLogVerbose()) {
        logger.info('Attempting Enhanced SSE connection', {
          attempt: this.retryCount + 1,
          url,
        });
      }

      const response = await fetch(url, {
        signal: this.abortController.signal,
        headers: {
          'Accept': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
          ...(this.lastEventId && { 'Last-Event-ID': this.lastEventId })
        },
        credentials: 'include'
      });

      clearTimeout(connectionTimeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error('No response body available for streaming');
      }

      if (this.canLogVerbose()) {
        logger.info('Enhanced SSE connection established', { url });
      }

      if (this.retryCount > 0) {
        this.emit('reconnected', { attempt: this.retryCount });
      }

      this.isConnected = true;
      this.retryCount = 0;
      this.clearOnlineListener();
      this.emit('open', { connected: true });

      await this.processStream(response.body);
    } catch (error) {
      clearTimeout(connectionTimeoutId);
      clearTimeout(streamTimeoutId);

      if (error instanceof Error && error.name === 'AbortError') {
        if (!this.isManuallyClosing && !this.isCompleted) {
          throw new Error('Connection timeout - server took too long to respond');
        }

        if (this.canLogVerbose()) {
          logger.info('SSE connection aborted due to manual close', { url: this.currentUrl });
        }
        return;
      }

      throw error;
    } finally {
      clearTimeout(connectionTimeoutId);
      clearTimeout(streamTimeoutId);
    }
  }

  /**
   * Process the SSE stream with enhanced chunking support
   */
  private async processStream(body: ReadableStream<Uint8Array>): Promise<void> {
    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          if (this.canLogVerbose()) {
            logger.info('SSE stream completed', { url: this.currentUrl });
          }
          break;
        }

        if (this.isManuallyClosing || this.isCompleted) {
          if (this.canLogVerbose()) {
            logger.info('SSE stream processing stopped due to close request', {
              isManuallyClosing: this.isManuallyClosing,
              isCompleted: this.isCompleted,
            });
          }
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const messages = this.parseSSEMessages(buffer);
        buffer = messages.remainder;

        for (const message of messages.parsed) {
          await this.handleMessage(message);
          if (this.isCompleted) {
            if (this.canLogVerbose()) {
              logger.info('Task completed - stopping SSE stream processing');
            }
            break;
          }
        }

        if (this.isCompleted) {
          break;
        }
      }
    } catch (error) {
      if (!this.isManuallyClosing && !this.isCompleted) {
        logger.error('Error processing SSE stream', { error });
        throw error;
      } else if (this.canLogVerbose()) {
        logger.info('SSE stream processing ended due to close request');
      }
    } finally {
      reader.releaseLock();
      this.isConnected = false;
    }
  }

  /**
   * Parse SSE messages from buffer
   */
  private parseSSEMessages(buffer: string): { parsed: SSEMessage[]; remainder: string } {
    const messages: SSEMessage[] = [];
    const lines = buffer.split('\n');
    let remainder = '';
    let currentMessage: Partial<SSEMessage> = {};

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      if (i === lines.length - 1 && !buffer.endsWith('\n')) {
        remainder = line;
        break;
      }

      if (line === '') {
        if (currentMessage.data !== undefined) {
          messages.push(currentMessage as SSEMessage);
        }
        currentMessage = {};
      } else if (line.startsWith('data: ')) {
        const data = line.slice(6);
        try {
          currentMessage.data = JSON.parse(data);
          currentMessage.type = currentMessage.data.type || currentMessage.data.message_type || 'message';
        } catch {
          currentMessage.data = data;
          currentMessage.type = 'text';
        }
      } else if (line.startsWith('id: ')) {
        currentMessage.id = line.slice(4);
        this.lastEventId = currentMessage.id;
      } else if (line.startsWith('retry: ')) {
        currentMessage.retry = parseInt(line.slice(7));
      } else if (line.startsWith('event: ')) {
        currentMessage.type = line.slice(7);
      }
    }

    return { parsed: messages, remainder };
  }

  /**
   * Handle individual SSE messages with chunking support
   */
  private async handleMessage(message: SSEMessage): Promise<void> {
    logger.debug('SSE message received', { type: message.type });

    if (message.type === 'content_chunk') {
      this.handleContentChunk(message.data);
      return;
    }

    this.emit(message.type, message.data);

    if (message.type === 'completed' || message.type === 'error') {
      if (this.canLogVerbose()) {
        logger.info('Task terminal event received - closing SSE connection', {
          type: message.type,
        });
      }
      this.isCompleted = true;
      this.close();
    }
  }

  /**
   * Handle chunked content for large AI data
   */
  private handleContentChunk(data: any): void {
    const { taskId, chunkId, content, position, totalSize, isComplete } = data;

    void chunkId;

    if (!this.contentBuffer.has(taskId)) {
      this.contentBuffer.set(taskId, {
        chunks: new Map(),
        totalSize: totalSize || 0,
        received: 0
      });
    }

    const buffer = this.contentBuffer.get(taskId)!;
    buffer.chunks.set(position, content);
    buffer.received += content.length;

    this.emit('content_progress', {
      taskId,
      received: buffer.received,
      total: buffer.totalSize,
      progress: buffer.totalSize > 0 ? (buffer.received / buffer.totalSize) * 100 : 0
    });

    if (isComplete) {
      const fullContent = this.reconstructContent(taskId);
      this.emit('content_complete', { taskId, content: fullContent });
      this.contentBuffer.delete(taskId);
    }
  }

  private reconstructContent(taskId: string): string {
    const buffer = this.contentBuffer.get(taskId);
    if (!buffer) return '';

    const sortedChunks = Array.from(buffer.chunks.entries())
      .sort(([a], [b]) => a - b)
      .map(([, content]) => content);

    return sortedChunks.join('');
  }

  /**
   * Schedule reconnection with exponential backoff and optional jitter
   */
  private scheduleReconnect(): void {
    if (this.isManuallyClosing || this.isCompleted) {
      if (this.canLogVerbose()) {
        logger.info('Skipping SSE reconnect - connection closed or completed', {
          isManuallyClosing: this.isManuallyClosing,
          isCompleted: this.isCompleted,
        });
      }
      return;
    }

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    const delay = this.getReconnectDelay();

    if (typeof window !== 'undefined' && 'onLine' in navigator && navigator.onLine === false) {
      if (this.canLogVerbose()) {
        logger.info('Browser offline detected, waiting for network before reconnecting');
      }
      this.emit('offline_wait', { attempt: this.retryCount + 1 });
      this.setOnlineListener(() => {
        if (this.canLogVerbose()) {
          logger.info('Network restored, scheduling SSE reconnect');
        }
        this.scheduleReconnect();
      });
      return;
    }

    if (this.canLogVerbose()) {
      logger.info('Scheduling SSE reconnect', {
        delay,
        attempt: this.retryCount + 1,
      });
    }

    this.emit('reconnecting', {
      attempt: this.retryCount + 1,
      delay,
    });

    this.reconnectTimer = setTimeout(() => {
      if (!this.isManuallyClosing && !this.isCompleted) {
        this.retryCount++;
        void this.connect();
      }
    }, delay);
  }

  addEventListener(type: string, listener: (data: any) => void): void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, []);
    }
    this.listeners.get(type)!.push(listener);
  }

  removeEventListener(type: string, listener: (data: any) => void): void {
    const listeners = this.listeners.get(type);
    if (!listeners) {
      return;
    }
    const index = listeners.indexOf(listener);
    if (index > -1) {
      listeners.splice(index, 1);
    }
  }

  private emit(type: string, data: any): void {
    const listeners = this.listeners.get(type);
    if (!listeners) {
      return;
    }
    listeners.forEach(listener => {
      try {
        listener(data);
      } catch (error) {
        logger.error(`Error in SSE listener for ${type}`, { error });
      }
    });
  }

  close(): void {
    if (this.canLogVerbose()) {
      logger.info('Closing Enhanced SSE connection', { url: this.currentUrl });
    }

    this.isManuallyClosing = true;
    this.isCompleted = true;

    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    this.clearOnlineListener();

    this.isConnected = false;
    this.retryCount = 0;
    this.contentBuffer.clear();
    this.emit('close', { reason: 'manual_close' });
  }

  get readyState(): number {
    return this.isConnected ? 1 : 0;
  }

  get connected(): boolean {
    return this.isConnected;
  }

  private async resolveUrl(): Promise<string> {
    const resolved = await this.urlFactory();
    this.currentUrl = resolved;
    return resolved;
  }

  private getReconnectDelay(): number {
    const exponential = this.options.retryDelay * Math.pow(this.options.backoffMultiplier, this.retryCount);
    const capped = Math.min(exponential, this.options.maxRetryDelay);
    const jitter = this.options.jitterMs > 0 ? Math.floor(Math.random() * this.options.jitterMs) : 0;
    return capped + jitter;
  }

  private setOnlineListener(callback: () => void): void {
    if (typeof window === 'undefined') {
      callback();
      return;
    }

    this.clearOnlineListener();
    this.pendingOnlineListener = () => {
      this.clearOnlineListener();
      if (!this.isManuallyClosing && !this.isCompleted) {
        callback();
      }
    };

    window.addEventListener('online', this.pendingOnlineListener, { once: true });
  }

  private clearOnlineListener(): void {
    if (this.pendingOnlineListener && typeof window !== 'undefined') {
      window.removeEventListener('online', this.pendingOnlineListener);
      this.pendingOnlineListener = null;
    }
  }
}
