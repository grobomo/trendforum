# TrendForum TODO

## Session Handoff (2026-04-26)
MVP is COMPLETE and VERIFIED. Working in worktree `trendforum-build` on branch `001-T001-create-forum-app`.
40 source files, all API endpoints tested E2E, Vite build passes (183KB JS).
Run from: `projects/trendforum/` — `npm run dev` starts Express :3847 + Vite :5173.
Login with dev WiFi password from prisma/seed.ts.
No Docker available locally (use EC2 spot via aws skill if needed).

## Completed (v0.1.0 MVP)
- Project scaffolding, Prisma schema, Express backend, React frontend
- Full E2E verified: auth, posts, comments, votes, reports, mod, feed
- Prisma singleton refactor, README
- Search (GET /api/search?q= with header search bar + results page)
- Security headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy)

## Next (priority order)

### Coconut Integration Module
- [ ] T002: Create reply generator (src/server/coconut/replies.ts) — pluggable template-based replies, ready for LLM swap
- [ ] T003: Create CoconutBot class (src/server/coconut/index.ts) — poll /api/feed, track last-seen timestamp, post replies via Prisma
- [ ] T004: Create admin API routes (src/server/routes/coconut.ts) — start/stop/status endpoints, admin-only
- [ ] T005: Wire coconut into server (src/server/index.ts) — register routes, auto-start option
- [ ] T006: Verify coconut E2E — start bot, create post, confirm bot reply appears

### Backlog
- [ ] T007: Mobile responsive polish (sidebar drawer, smaller cards on mobile)
- [ ] T008: Error boundaries in React for graceful failure
- [ ] T009: Image upload support (S3 or local storage)
- [ ] T010: GitHub publish (grobomo account — generic tool, no PII)
