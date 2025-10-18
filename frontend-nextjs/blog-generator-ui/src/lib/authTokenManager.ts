import { logger } from '@/lib/logger';

const EXPIRY_LEEWAY_MS = 60 * 1000; // Refresh token 1 minute before expiry
const FALLBACK_TTL_MS = 55 * 60 * 1000; // 55 minutes default when exp missing

class AuthTokenError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
    this.name = 'AuthTokenError';
  }
}

function decodeJwtPayload(token: string): Record<string, any> | null {
  try {
    const parts = token.split('.');
    if (parts.length < 2) {
      return null;
    }

    const payload = parts[1]
      .replace(/-/g, '+')
      .replace(/_/g, '/');

    let decoded: string;
    if (typeof window !== 'undefined' && typeof window.atob === 'function') {
      decoded = window.atob(payload);
    } else if (typeof globalThis.atob === 'function') {
      decoded = globalThis.atob(payload);
    } else if (typeof Buffer !== 'undefined') {
      decoded = Buffer.from(payload, 'base64').toString('utf8');
    } else {
      throw new Error('No base64 decoder available');
    }

    return JSON.parse(decoded);
  } catch (error) {
    logger.warn('Failed to decode JWT payload', { error });
    return null;
  }
}

class AuthTokenManager {
  private cachedToken: string | null = null;
  private expiresAt: number | null = null;
  private inFlight: Promise<string> | null = null;

  async getToken(options: { forceRefresh?: boolean } = {}): Promise<string | null> {
    const { forceRefresh = false } = options;

    if (!forceRefresh && this.cachedToken && this.expiresAt && Date.now() < this.expiresAt) {
      return this.cachedToken;
    }

    if (this.inFlight) {
      try {
        return await this.inFlight;
      } catch (error) {
        if (error instanceof AuthTokenError && error.status === 401) {
          throw error;
        }
        return null;
      }
    }

    this.inFlight = this.fetchAndCacheToken();

    try {
      const token = await this.inFlight;
      this.cachedToken = token;
      return token;
    } catch (error) {
      if (error instanceof AuthTokenError && error.status === 401) {
        throw error;
      }
      logger.warn('Auth token request failed', { error });
      return null;
    } finally {
      this.inFlight = null;
    }
  }

  invalidateToken() {
    this.cachedToken = null;
    this.expiresAt = null;
  }

  private async fetchAndCacheToken(): Promise<string> {
    const response = await fetch('/api/auth/jwt-token', {
      method: 'GET',
      credentials: 'include',
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => '');
      const message = errorText || `Failed to fetch auth token (status ${response.status})`;
      this.invalidateToken();
      throw new AuthTokenError(message, response.status);
    }

    const data = await response.json().catch(() => ({}));
    const token: string | undefined = data?.token;

    if (!token) {
      this.invalidateToken();
      throw new AuthTokenError('Auth token endpoint returned no token');
    }

    this.setToken(token);
    return token;
  }

  private setToken(token: string) {
    this.cachedToken = token;

    const payload = decodeJwtPayload(token);
    if (payload?.exp) {
      this.expiresAt = payload.exp * 1000 - EXPIRY_LEEWAY_MS;
    } else {
      this.expiresAt = Date.now() + FALLBACK_TTL_MS;
    }
  }
}

export const authTokenManager = new AuthTokenManager();
export { AuthTokenError };
