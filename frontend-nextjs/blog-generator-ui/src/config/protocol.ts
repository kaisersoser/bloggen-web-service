import { VERBOSE_LOGGING_ENABLED } from '@/lib/logger/env';
/**
 * Protocol configuration for frontend
 * Reads from environment variables to determine HTTP/HTTPS mode
 */

// Read protocol mode from environment (set in .env.local)
const PROTOCOL_MODE = process.env.NEXT_PUBLIC_PROTOCOL_MODE || 'https';
const FRONTEND_HOST = process.env.NEXT_PUBLIC_FRONTEND_HOST || 'localhost';
const FRONTEND_PORT = process.env.NEXT_PUBLIC_FRONTEND_PORT || '3001';
const BACKEND_HOST = process.env.NEXT_PUBLIC_BACKEND_HOST || 'localhost';
const BACKEND_PORT = process.env.NEXT_PUBLIC_BACKEND_PORT || '5000';

export class ProtocolConfig {
  static readonly protocolMode = PROTOCOL_MODE as 'http' | 'https';
  static readonly frontendHost = FRONTEND_HOST;
  static readonly frontendPort = FRONTEND_PORT;
  static readonly backendHost = BACKEND_HOST;
  static readonly backendPort = BACKEND_PORT;

  static get isHttps(): boolean {
    return this.protocolMode === 'https';
  }

  static get protocol(): string {
    return this.protocolMode;
  }

  static getFrontendUrl(): string {
    return `${this.protocol}://${this.frontendHost}:${this.frontendPort}`;
  }

  static getBackendUrl(): string {
    return `${this.protocol}://${this.backendHost}:${this.backendPort}`;
  }

  static getApiBaseUrl(): string {
    return this.getBackendUrl();
  }

  static logConfig(): void {
    if (!VERBOSE_LOGGING_ENABLED) {
      return;
    }

    const details = {
      mode: this.protocol.toUpperCase(),
      frontendUrl: this.getFrontendUrl(),
      backendUrl: this.getBackendUrl(),
    };

    if (typeof window !== 'undefined') {
      void import('@/lib/logger')
        .then(({ logger }) => {
          if (logger.shouldLog('info')) {
            logger.info('🔧 Protocol configuration (client)', details);
          }
        })
        .catch(() => {
          // Swallow logging transport errors silently
        });
    } else {
      void import('@/lib/logger/server')
        .then(({ serverLogger }) => {
          serverLogger.info('🔧 Protocol configuration (server)', details);
        })
        .catch(() => {
          // Silent failure if logger unavailable during build
        });
    }
  }
}

// Export convenience functions
export const isHttpsMode = () => ProtocolConfig.isHttps;
export const getFrontendUrl = () => ProtocolConfig.getFrontendUrl();
export const getBackendUrl = () => ProtocolConfig.getBackendUrl();
export const getApiBaseUrl = () => ProtocolConfig.getApiBaseUrl();

// Log configuration on import (only in browser)
if (typeof window !== 'undefined') {
  ProtocolConfig.logConfig();
}
