/**
 * Simple EventSource wrapper to test enhanced message reception
 * Bypasses TimeoutResistantSSE complexity for debugging
 */

import { logger } from '@/lib/logger';
import { VERBOSE_LOGGING_ENABLED } from '@/lib/logger/env';

export class SimpleSSE {
  private eventSource: EventSource | null = null;
  private url: string;

  private canLogVerbose(): boolean {
    return VERBOSE_LOGGING_ENABLED && logger.shouldLog('info');
  }

  constructor(url: string) {
    this.url = url;
  }

  async connect(
    onMessage: (data: any) => void,
    onError: (error: any) => void
  ): Promise<void> {
    if (this.canLogVerbose()) {
      logger.info('SimpleSSE attempting connection', { url: this.url });
    }
    
    try {
      this.eventSource = new EventSource(this.url);
      
      this.eventSource.onopen = () => {
        if (this.canLogVerbose()) {
          logger.info('SimpleSSE connection opened', { url: this.url });
        }
      };
      
      this.eventSource.onmessage = (event) => {
        logger.debug('SimpleSSE raw message received', { data: event.data });
        try {
          const data = JSON.parse(event.data);
          logger.debug('SimpleSSE parsed message', { type: data.type, data });
          onMessage(data);
        } catch (err) {
          logger.error('SimpleSSE failed to parse message', { error: err });
        }
      };
      
      this.eventSource.onerror = (error) => {
        logger.error('SimpleSSE connection error', { error });
        onError(error);
      };
      
    } catch (error) {
      logger.error('SimpleSSE failed to create EventSource', { error });
      throw error;
    }
  }

  close(): void {
    if (this.eventSource) {
      if (this.canLogVerbose()) {
        logger.info('SimpleSSE closing connection', { url: this.url });
      }
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}
