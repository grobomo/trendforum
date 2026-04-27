import express from 'express';
import cors from 'cors';
import compression from 'compression';
import path from 'path';
import { fileURLToPath } from 'url';
import authRoutes from './routes/auth.js';
import subforumRoutes from './routes/subforums.js';
import postRoutes, { subforumPostsRouter } from './routes/posts.js';
import commentRoutes from './routes/comments.js';
import voteRoutes from './routes/votes.js';
import reportRoutes from './routes/reports.js';
import modRoutes from './routes/mod.js';
import feedRoutes from './routes/feed.js';

const app = express();
const PORT = parseInt(process.env.PORT || '3847', 10);

// Middleware
app.use(cors());
app.use(compression());
app.use(express.json());

// API routes
app.use('/api/auth', authRoutes);
app.use('/api/subforums', subforumRoutes);
app.use('/api/subforums', subforumPostsRouter); // GET /api/subforums/:slug/posts
app.use('/api/posts', postRoutes);
app.use('/api/posts', commentRoutes); // POST /api/posts/:id/comments
app.use('/api/vote', voteRoutes);
app.use('/api/report', reportRoutes);
app.use('/api/mod', modRoutes);
app.use('/api/feed', feedRoutes);

// Serve static frontend in production
if (process.env.NODE_ENV === 'production') {
  const __dirname = path.dirname(fileURLToPath(import.meta.url));
  const clientDist = path.join(__dirname, '../../dist/client');
  app.use(express.static(clientDist));
  app.get('*', (_req, res) => {
    res.sendFile(path.join(clientDist, 'index.html'));
  });
}

app.listen(PORT, () => {
  console.log(`TrendForum running on http://localhost:${PORT}`);
});

export default app;
