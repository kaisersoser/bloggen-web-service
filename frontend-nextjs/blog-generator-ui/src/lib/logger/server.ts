import { promises as fs } from 'fs';
import path from 'path';

import { DEFAULT_LOG_LEVEL, type LogLevel, parseLogLevel, shouldLog } from './levels';
import { buildLogPayload, type LogMessage, type LogPayload } from './shared';

const LOG_DIRECTORY = path.join(process.cwd(), 'logs');
const LOG_FILE_PATH = path.join(LOG_DIRECTORY, 'frontend-webApp.log');
const MAX_LOG_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10MB rotation threshold
const ROTATED_FILENAME = 'frontend-webApp.log.bak';

let activeServerLogLevel: LogLevel = resolveInitialServerLevel();

function resolveInitialServerLevel(): LogLevel {
  return (
    parseLogLevel(process.env.LOG_LEVEL ?? process.env.NEXT_PUBLIC_LOG_LEVEL) ?? DEFAULT_LOG_LEVEL
  );
}

async function ensureLogDirectoryExists(): Promise<void> {
  await fs.mkdir(LOG_DIRECTORY, { recursive: true });
}

async function rotateLogFileIfNeeded(): Promise<void> {
  try {
    const stats = await fs.stat(LOG_FILE_PATH);
    if (stats.size > MAX_LOG_FILE_SIZE_BYTES) {
      await fs.rename(LOG_FILE_PATH, path.join(LOG_DIRECTORY, ROTATED_FILENAME));
    }
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'ENOENT') {
      throw error;
    }
  }
}

function formatContext(context?: Record<string, unknown>): string {
  if (!context || Object.keys(context).length === 0) {
    return '';
  }

  try {
    return ` | context=${JSON.stringify(context)}`;
  } catch {
    return ' | context=[unserializable]';
  }
}

function formatLogLine({ level, message, context, timestamp, source }: LogPayload): string {
  const levelTag = level.toUpperCase().padEnd(5, ' ');
  const sourceTag = source ? ` (${source})` : '';
  return `[${timestamp}] ${levelTag}${sourceTag} ${message}${formatContext(context)}\n`;
}

async function appendPayload(payload: LogPayload): Promise<void> {
  await ensureLogDirectoryExists();
  await rotateLogFileIfNeeded();

  await fs.appendFile(LOG_FILE_PATH, formatLogLine(payload), { encoding: 'utf8' });
}

export async function writeServerLog(payload: LogPayload): Promise<void> {
  if (!shouldLog(payload.level, activeServerLogLevel)) {
    return;
  }

  await appendPayload(payload);
}

export function setServerLogLevel(level: LogLevel): void {
  activeServerLogLevel = level;
}

export function getServerLogLevel(): LogLevel {
  return activeServerLogLevel;
}

export function configureServerLogger(options: { level?: string }): void {
  if (options.level) {
    const parsed = parseLogLevel(options.level);
    if (parsed) {
      activeServerLogLevel = parsed;
    }
  }
}

async function logWithMeta(level: LogLevel, message: LogMessage, meta: unknown[]): Promise<void> {
  if (!shouldLog(level, activeServerLogLevel)) {
    return;
  }

  const payload = buildLogPayload(level, message, meta, 'server');
  await appendPayload(payload);
}

export const serverLogger = {
  error(message: LogMessage, ...meta: unknown[]): void {
    void logWithMeta('error', message, meta);
  },
  warn(message: LogMessage, ...meta: unknown[]): void {
    void logWithMeta('warn', message, meta);
  },
  info(message: LogMessage, ...meta: unknown[]): void {
    void logWithMeta('info', message, meta);
  },
  debug(message: LogMessage, ...meta: unknown[]): void {
    void logWithMeta('debug', message, meta);
  },
};

export function logServerEvent(level: LogLevel, message: LogMessage, ...meta: unknown[]): Promise<void> {
  return logWithMeta(level, message, meta);
}
