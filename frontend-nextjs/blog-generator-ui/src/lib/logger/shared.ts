import { type LogLevel } from './levels';

export type LogMessage = string | (() => string);

export type LogPayload = {
  level: LogLevel;
  message: string;
  context?: Record<string, unknown>;
  timestamp: string;
  source?: string;
};

const MAX_MESSAGE_LENGTH = 2000;
const MAX_CONTEXT_KEYS = 25;
const MAX_CONTEXT_ITEMS = 10;

export function resolveMessage(message: LogMessage): string {
  return typeof message === 'function' ? message() : message;
}

export function serializeError(error: Error): Record<string, unknown> {
  return {
    message: error.message,
    stack: error.stack,
    name: error.name,
  };
}

function clampMessage(message: string): string {
  if (message.length <= MAX_MESSAGE_LENGTH) {
    return message;
  }

  return `${message.slice(0, MAX_MESSAGE_LENGTH)}…`;
}

function pruneObject(context: Record<string, unknown>): Record<string, unknown> | undefined {
  const sanitized: Record<string, unknown> = {};
  let count = 0;
  for (const [key, value] of Object.entries(context)) {
    sanitized[key] = value instanceof Error ? serializeError(value) : value;
    count += 1;
    if (count >= MAX_CONTEXT_KEYS) {
      break;
    }
  }

  return Object.keys(sanitized).length > 0 ? sanitized : undefined;
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value);
}

function sanitizeMetaValue(value: unknown): unknown {
  if (value instanceof Error) {
    return serializeError(value);
  }
  if (value instanceof Date) {
    return value.toISOString();
  }
  if (Array.isArray(value)) {
    return value.slice(0, MAX_CONTEXT_ITEMS).map((item) => sanitizeMetaValue(item));
  }
  if (isPlainObject(value)) {
    return pruneObject(value as Record<string, unknown>) ?? {};
  }
  return value;
}

function normalizeMeta(meta: unknown[]): Record<string, unknown> | undefined {
  if (meta.length === 0) {
    return undefined;
  }

  if (meta.length === 1 && isPlainObject(meta[0])) {
    return pruneObject(meta[0] as Record<string, unknown>);
  }

  return {
    data: meta.slice(0, MAX_CONTEXT_ITEMS).map((value) => sanitizeMetaValue(value)),
  };
}

export function buildLogPayload(
  level: LogLevel,
  message: LogMessage,
  meta: unknown[],
  source: string
): LogPayload {
  return {
    level,
    message: clampMessage(resolveMessage(message)),
    context: normalizeMeta(meta),
    timestamp: new Date().toISOString(),
    source,
  };
}
