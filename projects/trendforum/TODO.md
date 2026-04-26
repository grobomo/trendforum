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

### Coconut Integration Module (DONE)
- [x] T002: Create reply generator (src/server/coconut/replies.ts) — pluggable template-based replies (PR #1)
- [x] T003: Create CoconutBot class (src/server/coconut/index.ts) — poll feed, reply via Prisma (PR #1)
- [x] T004: Create admin API routes (src/server/routes/coconut.ts) — start/stop/status, admin-only (PR #1)
- [x] T005: Wire coconut into server (src/server/index.ts) — routes + COCONUT_AUTOSTART env var (PR #1)
- [x] T006: Verify coconut E2E — 7/7 tests pass, bot replied, admin guard works (PR #1)

### Mobile Responsive (In Progress)
- [ ] T007a: Add hamburger menu + sidebar drawer overlay on mobile (Layout.tsx)
- [ ] T007b: Compact header on small screens (collapsible search)
- [ ] T007c: Tighter PostCard spacing on mobile

### Backlog
- [ ] T008: Error boundaries in React for graceful failure
- [ ] T009: Image upload support (S3 or local storage)
- [ ] T010: GitHub publish (grobomo account — generic tool, no PII)
