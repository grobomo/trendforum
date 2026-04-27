# TrendForum

Anonymous community forum with Reddit-like UX. No accounts, no tracking — just a shared password to prove you belong.

## How It Works

1. Enter the shared community password to get access
2. Get an anonymous session token (no username, no email, no account)
3. Post, comment, and vote — nobody can link activity to your identity

Each post thread assigns you a random display name (e.g., `Anon-A7X`) so conversations are followable, but names don't carry across posts.

## Quick Start

```bash
# Install
npm install

# Set up database
npx prisma db push
npm run db:seed

# Run (starts Express on :3847 + Vite on :5173)
npm run dev
```

Open http://localhost:5173 and log in with the dev password: see `prisma/seed.ts`.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Tailwind CSS |
| Backend | Node.js + Express + TypeScript |
| Database | SQLite (dev) via Prisma ORM |
| Auth | Shared-secret password + JWT (no user ID) |

## Privacy Guarantees

- Session tokens contain NO user identifier (just a random `jti` and expiry)
- No IP logging, no fingerprinting, no analytics
- Database stores no author field on posts/comments
- Display names are per-post-thread only (hash of session + post ID)
- Rate limiting by token `jti`, not by IP

## Features

- Subforums with hot/new/top sorting
- Nested comments with voting
- Image uploads (JPEG, PNG, GIF, WebP — 5MB limit)
- Real-time updates via WebSocket (new posts/comments appear live)
- Content moderation (admin reports queue)
- Coconut bot — automated community participant
- Mobile responsive with hamburger menu
- Per-IP WebSocket rate limiting
- React error boundaries

## API

```
POST /api/auth/verify        { password }              -> { token }
GET  /api/subforums                                    -> subforum list
GET  /api/posts?sort=hot|new|top&page=1                -> all posts
GET  /api/subforums/:slug/posts?sort=hot|new|top       -> subforum posts
POST /api/posts              { subforumId, title, body? }
GET  /api/posts/:id                                    -> post + comments
POST /api/posts/:id/comments { body, parentId? }
POST /api/vote               { postId?, commentId?, value: 1|-1 }
POST /api/report             { postId?, commentId?, reason }
GET  /api/feed?since=<iso>                             -> new activity (Coconut)
GET  /api/mod/reports                                  -> admin only
POST /api/mod/action         { action, targetId, targetType }
POST /api/upload             multipart/form-data       -> { url }
```

## Docker

```bash
docker compose up --build
```

Runs on port 3847. Set `JWT_SECRET` in environment for production.

## License

MIT
