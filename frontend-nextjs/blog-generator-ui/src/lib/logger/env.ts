export const VERBOSE_LOGGING_ENABLED =
  process.env.NODE_ENV !== 'production' ||
  process.env.NEXT_PUBLIC_ENABLE_VERBOSE_LOGGING === 'true';
