import { Router } from 'express';
import bcrypt from 'bcryptjs';
import { prisma } from '../db.js';
import { generateToken } from '../auth.js';
import { requireAuth } from '../middleware/requireAuth.js';

const router = Router();

// Register a pseudonym (must be authenticated first)
router.post('/register', requireAuth, async (req, res) => {
  const { pseudonym, password } = req.body;

  if (!pseudonym || typeof pseudonym !== 'string' || pseudonym.length < 3 || pseudonym.length > 20) {
    res.status(400).json({ error: 'Pseudonym must be 3-20 characters' });
    return;
  }

  if (!/^[a-zA-Z0-9_-]+$/.test(pseudonym)) {
    res.status(400).json({ error: 'Pseudonym can only contain letters, numbers, hyphens, and underscores' });
    return;
  }

  if (!password || typeof password !== 'string' || password.length < 6) {
    res.status(400).json({ error: 'Password must be at least 6 characters' });
    return;
  }

  // Reserved names
  const reserved = ['admin', 'moderator', 'mod', 'coconut', 'system', 'anon', 'anonymous'];
  if (reserved.includes(pseudonym.toLowerCase())) {
    res.status(400).json({ error: 'That pseudonym is reserved' });
    return;
  }

  const existing = await prisma.profile.findUnique({ where: { pseudonym } });
  if (existing) {
    res.status(409).json({ error: 'Pseudonym already taken' });
    return;
  }

  const passwordHash = await bcrypt.hash(password, 10);
  const profile = await prisma.profile.create({
    data: { pseudonym, passwordHash },
  });

  const token = generateToken('member', { id: profile.id, pseudonym: profile.pseudonym });
  res.json({ token, profile: { id: profile.id, pseudonym: profile.pseudonym } });
});

// Login as existing pseudonym (must have shared password session first)
router.post('/login', requireAuth, async (req, res) => {
  const { pseudonym, password } = req.body;

  if (!pseudonym || !password) {
    res.status(400).json({ error: 'Pseudonym and password required' });
    return;
  }

  const profile = await prisma.profile.findUnique({ where: { pseudonym } });
  if (!profile) {
    res.status(401).json({ error: 'Invalid pseudonym or password' });
    return;
  }

  const valid = await bcrypt.compare(password, profile.passwordHash);
  if (!valid) {
    res.status(401).json({ error: 'Invalid pseudonym or password' });
    return;
  }

  const token = generateToken('member', { id: profile.id, pseudonym: profile.pseudonym });
  res.json({ token, profile: { id: profile.id, pseudonym: profile.pseudonym } });
});

// Get current profile info
router.get('/me', requireAuth, async (req, res) => {
  const profileId = req.token?.profileId;
  if (!profileId) {
    res.json({ profile: null });
    return;
  }

  const profile = await prisma.profile.findUnique({
    where: { id: profileId },
    select: {
      id: true,
      pseudonym: true,
      createdAt: true,
      _count: { select: { posts: true, comments: true } },
    },
  });

  res.json({ profile });
});

// Drop profile — return to anonymous mode
router.post('/drop', requireAuth, async (req, res) => {
  const token = generateToken('member');
  res.json({ token });
});

// Public profile page
router.get('/:pseudonym', async (req, res) => {
  const profile = await prisma.profile.findUnique({
    where: { pseudonym: req.params.pseudonym },
    select: {
      pseudonym: true,
      createdAt: true,
      _count: { select: { posts: true, comments: true } },
      posts: {
        orderBy: { createdAt: 'desc' },
        take: 20,
        include: { subforum: true, _count: { select: { comments: true } } },
      },
    },
  });

  if (!profile) {
    res.status(404).json({ error: 'Profile not found' });
    return;
  }

  res.json({ profile });
});

export { router as profileRouter };
