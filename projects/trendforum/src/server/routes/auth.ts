import { Router } from 'express';
import { PrismaClient } from '@prisma/client';
import { verifyPassword, generateToken } from '../auth.js';
import { authLimiter } from '../middleware/rateLimit.js';

const router = Router();
const prisma = new PrismaClient();

router.post('/verify', authLimiter, async (req, res) => {
  const { password } = req.body;

  if (!password || typeof password !== 'string') {
    res.status(400).json({ error: 'Password required' });
    return;
  }

  const configHash = await prisma.config.findUnique({ where: { key: 'wifi_password_hash' } });
  const hash = configHash?.value || process.env.WIFI_PASSWORD_HASH;

  if (!hash) {
    res.status(500).json({ error: 'Server not configured' });
    return;
  }

  const valid = await verifyPassword(password, hash);
  if (!valid) {
    res.status(401).json({ error: 'Invalid password' });
    return;
  }

  const token = generateToken('trender');
  res.json({ token });
});

router.post('/admin', authLimiter, async (req, res) => {
  const { password } = req.body;

  if (!password || typeof password !== 'string') {
    res.status(400).json({ error: 'Password required' });
    return;
  }

  const configHash = await prisma.config.findUnique({ where: { key: 'admin_password_hash' } });
  const hash = configHash?.value || process.env.ADMIN_PASSWORD_HASH;

  if (!hash) {
    res.status(500).json({ error: 'Admin not configured' });
    return;
  }

  const valid = await verifyPassword(password, hash);
  if (!valid) {
    res.status(401).json({ error: 'Invalid password' });
    return;
  }

  const token = generateToken('admin');
  res.json({ token });
});

export { router as authRouter };
