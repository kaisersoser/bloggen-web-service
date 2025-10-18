export type LogLevel = 'error' | 'warn' | 'info' | 'debug';

export const LOG_LEVEL_PRIORITY: Record<LogLevel, number> = {
  error: 0,
  warn: 1,
  info: 2,
  debug: 3,
};

const ALLOWED_LEVELS = Object.keys(LOG_LEVEL_PRIORITY) as LogLevel[];

export const DEFAULT_LOG_LEVEL: LogLevel = parseLogLevel(
  process.env.NEXT_PUBLIC_LOG_LEVEL ?? process.env.LOG_LEVEL
) ?? 'warn';

export function parseLogLevel(value?: string | null): LogLevel | null {
  if (!value) {
    return null;
  }

  const normalized = value.toLowerCase().trim();
  return (ALLOWED_LEVELS.find((level) => level === normalized) ?? null) as LogLevel | null;
}

export function shouldLog(level: LogLevel, threshold: LogLevel = DEFAULT_LOG_LEVEL): boolean {
  return LOG_LEVEL_PRIORITY[level] <= LOG_LEVEL_PRIORITY[threshold];
}
