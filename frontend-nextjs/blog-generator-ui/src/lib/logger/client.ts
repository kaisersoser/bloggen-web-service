'use client'

import { DEFAULT_LOG_LEVEL, type LogLevel, parseLogLevel, shouldLog } from './levels';
import { buildLogPayload, type LogMessage, type LogPayload } from './shared';

const LOG_ENDPOINT = '/api/logs';

let activeLogLevel: LogLevel = DEFAULT_LOG_LEVEL;

function sendPayload(payload: LogPayload): void {
  try {
    if (typeof navigator !== 'undefined' && typeof navigator.sendBeacon === 'function') {
      const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });
      const success = navigator.sendBeacon(LOG_ENDPOINT, blob);
      if (success) {
        return;
      }
    }
  } catch {
    // Ignore sendBeacon errors and fall back to fetch
  }

  if (typeof fetch !== 'undefined') {
    void fetch(LOG_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      keepalive: true,
      body: JSON.stringify(payload),
    }).catch(() => {
      // Silently ignore logging transport errors on the client
    });
  }
}

function log(level: LogLevel, message: LogMessage, ...meta: unknown[]): void {
  if (!shouldLog(level, activeLogLevel)) {
    return;
  }

  const payload = buildLogPayload(level, message, meta, 'browser');

  if (typeof window === 'undefined') {
    return;
  }

  queueMicrotask(() => sendPayload(payload));
}

export const logger = {
  setLevel(level: LogLevel): void {
    activeLogLevel = level;
  },
  getLevel(): LogLevel {
    return activeLogLevel;
  },
  error(message: LogMessage, ...meta: unknown[]): void {
    log('error', message, ...meta);
  },
  warn(message: LogMessage, ...meta: unknown[]): void {
    log('warn', message, ...meta);
  },
  info(message: LogMessage, ...meta: unknown[]): void {
    log('info', message, ...meta);
  },
  debug(message: LogMessage, ...meta: unknown[]): void {
    log('debug', message, ...meta);
  },
  shouldLog(level: LogLevel): boolean {
    return shouldLog(level, activeLogLevel);
  },
  configure(options: { level?: string }): void {
    if (options.level) {
      const parsed = parseLogLevel(options.level);
      if (parsed) {
        activeLogLevel = parsed;
      }
    }
  },
};

export type { LogLevel };
