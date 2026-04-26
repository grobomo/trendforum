import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import { authRouter } from './routes/auth.js';
import { subforumsRouter } from './routes/subforums.js';
import { postsRouter } from './routes/posts.js';
import { commentsRouter } from './routes/comments.js';
import { votesRouter } from './routes/votes.js';
import { reportsRouter } from './routes/reports.js';
import { modRouter } from './routes/mod.js';
import { feedRouter } from './routes/feed.js';
import { searchRouter } from './routes/search.js';
import { coconutRouter } from './routes/coconut.js';
import { uploadRouter } from './routes/upload.js';
import { profileRouter } from './routes/profile.js';
import { coconutBot } from './coconut/index.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app = express();
const PORT = process.env.PORT || 3847;

app.use(cors());
app.use(express.json({ limit: '1mb' }));
app.disable('x-powered-by');

// Security headers
app.use((_req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('Referrer-Policy', 'no-referrer');
  next();
});

app.use('/api/auth', authRouter);
app.use('/api/subforums', subforumsRouter);
app.use('/api', postsRouter);
app.use('/api', commentsRouter);
app.use('/api', votesRouter);
app.use('/api', reportsRouter);
app.use('/api/mod', modRouter);
app.use('/api', feedRouter);
app.use('/api', searchRouter);
app.use('/api/coconut', coconutRouter);
app.use('/api', uploadRouter);
app.use('/api/profile', profileRouter);

// Serve uploaded images
app.use('/uploads', express.static(path.resolve(process.cwd(), 'uploads')));

// Serve static files in production
const clientDir = path.resolve(__dirname, '../client');
app.use(express.static(clientDir));
app.get('*', (_req, res) => {
  res.sendFile(path.join(clientDir, 'index.html'));
});

app.listen(PORT, () => {
  console.log(`TrendForum running on http://localhost:${PORT}`);
  if (process.env.COCONUT_AUTOSTART === '1') {
    coconutBot.start();
  }
});
