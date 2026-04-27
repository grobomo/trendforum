import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import { v4 as uuidv4 } from 'uuid';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret-change-me';
const TOKEN_EXPIRY = '24h';

export interface TokenPayload {
  role: 'trender' | 'admin';
  jti: string;
  iat: number;
  exp: number;
}

/**
 * Verify WiFi password against stored hash.
 * Returns a signed JWT with NO user identifier — just role + random jti.
 */
export async function verifyPassword(password: string): Promise<string | null> {
  const config = await prisma.config.findUnique({ where: { key: 'wifi_password_hash' } });
  if (!config) return null;

  const valid = await bcrypt.compare(password, config.value);
  if (!valid) return null;

  const jti = uuidv4();
  const token = jwt.sign({ role: 'trender', jti }, JWT_SECRET, { expiresIn: TOKEN_EXPIRY });
  return token;
}

/**
 * Verify admin password.
 */
export async function verifyAdminPassword(password: string): Promise<string | null> {
  const config = await prisma.config.findUnique({ where: { key: 'admin_password_hash' } });
  if (!config) return null;

  const valid = await bcrypt.compare(password, config.value);
  if (!valid) return null;

  const jti = uuidv4();
  const token = jwt.sign({ role: 'admin', jti }, JWT_SECRET, { expiresIn: TOKEN_EXPIRY });
  return token;
}

/**
 * Decode and verify a JWT token. Returns payload or null.
 */
export function verifyToken(token: string): TokenPayload | null {
  try {
    return jwt.verify(token, JWT_SECRET) as TokenPayload;
  } catch {
    return null;
  }
}

/**
 * Generate a random per-post-tree display name like "Trender-A7x"
 */
export function generateDisplayName(): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let suffix = '';
  for (let i = 0; i < 3; i++) {
    suffix += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return `Trender-${suffix}`;
}
