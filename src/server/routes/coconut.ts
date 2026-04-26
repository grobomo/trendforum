import { Router } from 'express';
import { requireAdmin } from '../middleware/requireAuth.js';
import { coconutBot } from '../coconut/index.js';

const router = Router();

router.post('/start', requireAdmin, (_req, res) => {
  if (coconutBot.running) {
    res.json({ message: 'Coconut is already running', ...coconutBot.status() });
    return;
  }
  coconutBot.start();
  res.json({ message: 'Coconut started', ...coconutBot.status() });
});

router.post('/stop', requireAdmin, (_req, res) => {
  if (!coconutBot.running) {
    res.json({ message: 'Coconut is not running', ...coconutBot.status() });
    return;
  }
  coconutBot.stop();
  res.json({ message: 'Coconut stopped', ...coconutBot.status() });
});

router.get('/status', (_req, res) => {
  res.json(coconutBot.status());
});

export { router as coconutRouter };
