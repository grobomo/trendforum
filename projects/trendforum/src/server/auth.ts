import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import crypto from 'crypto';

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret-change-me';

export interface TokenPayload {
  role: 'member' | 'admin';
  jti: string;
  iat: number;
  exp: number;
  profileId?: number;
  pseudonym?: string;
}

export function verifyPassword(password: string, hash: string): Promise<boolean> {
  return bcrypt.compare(password, hash);
}

export function generateToken(role: 'member' | 'admin' = 'member', profile?: { id: number; pseudonym: string }): string {
  const jti = crypto.randomUUID();
  const payload: Record<string, unknown> = { role, jti };
  if (profile) {
    payload.profileId = profile.id;
    payload.pseudonym = profile.pseudonym;
  }
  return jwt.sign(payload, JWT_SECRET, { expiresIn: '24h' });
}

export function verifyToken(token: string): TokenPayload | null {
  try {
    return jwt.verify(token, JWT_SECRET) as TokenPayload;
  } catch {
    return null;
  }
}

export function generateDisplayName(jti: string, postId: number): string {
  const hash = crypto.createHash('sha256').update(`${jti}:${postId}`).digest('hex');
  const suffix = hash.substring(0, 3).toUpperCase();
  return `Anon-${suffix}`;
}
