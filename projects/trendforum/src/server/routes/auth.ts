import { Router } from 'express';
import { verifyPassword, verifyAdminPassword } from '../auth.js';
import { authLimiter } from '../middleware/rateLimit.js';

const router = Router();

/**
 * POST /api/auth/verify
 * Body: { password: string, admin?: boolean }
 * Returns: { token: string } or 401
 */
router.post('/verify', authLimiter, async (req, res) => {
  const { password, admin } = req.body;
  if (!password || typeof password !== 'string') {
    res.status(400).json({ error: 'Password required' });
    return;
  }

  const token = admin
    ? await verifyAdminPassword(password)
    : await verifyPassword(password);

  if (!token) {
    res.status(401).json({ error: 'Invalid password' });
    return;
  }

  res.json({ token });
});

export default router;
