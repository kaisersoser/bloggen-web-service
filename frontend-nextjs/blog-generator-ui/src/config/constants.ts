// Centralized frontend configuration & role limits
// Keeps business rules and environment-derived configuration in one place.

// Import protocol configuration
import { getApiBaseUrl, getWebSocketUrl } from './protocol';

// API Configuration - Dynamically determined by protocol mode
export const API_BASE_URL = getApiBaseUrl();

// Next.js API routes (always use relative paths for same-origin)
export const NEXT_API_BASE = "";  // Relative to current origin

// WebSocket configuration - matches API protocol
export const WS_BASE_URL = getWebSocketUrl();

// Monthly generation limits (-1 means unlimited)
export const ROLE_LIMITS: Record<string, { MONTHLY: number }> = {
  FREE: { MONTHLY: 3 },      // As per documented specification
  PREMIUM: { MONTHLY: 50 },
  ADMIN: { MONTHLY: -1 }
};

export function canUserGenerate(role: string, monthlyGenerations: number): boolean {
  const limit = ROLE_LIMITS[role]?.MONTHLY ?? 0;
  if (limit === -1) return true;
  return monthlyGenerations < limit;
}

export function remainingGenerations(role: string, monthlyGenerations: number): number {
  const limit = ROLE_LIMITS[role]?.MONTHLY ?? 0;
  if (limit === -1) return Infinity;
  return Math.max(0, limit - monthlyGenerations);
}

// Blog generation step to color mapping (centralized so UI components stay consistent)
export const STEP_COLOR_MAP: Record<string, string> = {
  initialization: 'text-blue-400',
  research: 'text-yellow-400',
  'content generation': 'text-green-400',
  'fact checking': 'text-purple-400',
  finalization: 'text-cyan-400',
  processing: 'text-gray-400'
};
