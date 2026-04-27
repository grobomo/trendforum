import rateLimit from 'express-rate-limit';
import { Request } from 'express';

/**
 * Rate limiter keyed by JWT jti (per-session), NOT by IP.
 * Privacy-first: we never log or key on IP addresses.
 */
export const apiLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute window
  max: 60, // 60 requests per minute per session
  keyGenerator: (req: Request) => {
    return req.tokenPayload?.jti || 'anonymous';
  },
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many requests, slow down.' },
});

/**
 * Stricter rate limit for auth attempts.
 * Keyed by a fixed string since pre-auth has no jti.
 * This is intentionally loose — we can't key by IP (privacy).
 */
export const authLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 10, // 10 auth attempts per minute globally
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many login attempts. Try again in a minute.' },
});
