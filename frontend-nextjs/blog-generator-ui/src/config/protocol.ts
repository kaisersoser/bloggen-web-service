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
    console.log(`🔧 Protocol Config: ${this.protocol.toUpperCase()} mode`);
    console.log(`   Frontend: ${this.getFrontendUrl()}`);
    console.log(`   Backend: ${this.getBackendUrl()}`);
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
