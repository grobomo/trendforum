# TrendForum

Anonymous community forum with Reddit-like UX. No accounts, no tracking — just a shared password to prove you belong.

## How It Works

1. Enter the shared community password to get access
2. Get an anonymous session token (no username, no email, no account)
3. Post, comment, and vote — nobody can link activity to your identity

Each post thread assigns you a random display name (e.g., `Anon-A7X`) so conversations are followable, but names don't carry across posts. Optionally claim a persistent pseudonym for identity across sessions.

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
| Markdown | marked + DOMPurify |

## Features

- **Subforums** with hot/new/top sorting and pagination
- **Nested comments** with voting and markdown rendering
- **Image uploads** (JPEG, PNG, GIF, WebP — 5MB limit)
- **User profiles** — optional persistent pseudonyms with profile pages (`/u/:name`)
- **Coconut bot** — AI-powered community participant (uses `claude -p`, falls back to templates)
- **Admin dashboard** — moderation queue at `/admin` with remove actions
- **Content moderation** — report posts/comments, admin review queue
- **Markdown** in posts and comments (bold, italic, code, links, lists, blockquotes)
- **Mobile responsive** with hamburger menu and collapsible search
- **Security** — rate limiting, input validation, XSS protection via DOMPurify
- React error boundaries

## Privacy Guarantees

- Session tokens contain NO user identifier (just a random `jti` and expiry)
- No IP logging, no fingerprinting, no analytics
- Database stores no author field on posts/comments (unless you opt in with a pseudonym)
- Display names are per-post-thread only (hash of session + post ID)
- Rate limiting by token `jti`, not by IP

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
POST /api/upload             multipart/form-data       -> { url }
GET  /api/search?q=<query>&page=1                      -> search results
POST /api/profile/register   { pseudonym, password }   -> { token, profile }
POST /api/profile/login      { pseudonym, password }   -> { token, profile }
GET  /api/profile/me                                   -> { profile }
GET  /api/profile/:pseudonym                           -> public profile
GET  /api/feed?since=<iso>                             -> new activity (Coconut)
GET  /api/coconut/status                               -> bot status
POST /api/coconut/start                                -> admin only
POST /api/coconut/stop                                 -> admin only
GET  /api/mod/reports                                  -> admin only
POST /api/mod/action         { action, targetId, targetType }
```

## E2E Tests

```bash
bash test-upload.sh      # 5 tests — image upload flow
bash test-coconut.sh     # 7 tests — bot lifecycle
bash test-profile.sh     # 10 tests — profiles, pseudonyms, pagination
```

## Docker

```bash
docker compose up --build
```

Runs on port 3847. Set `JWT_SECRET` in environment for production.

## License

MIT
