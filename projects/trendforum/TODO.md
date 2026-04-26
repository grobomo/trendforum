# TrendForum TODO

## Session Handoff (2026-04-26)
MVP is COMPLETE and VERIFIED. Working in worktree `trendforum-build` on branch `001-T001-create-forum-app`.
All 38 source files built, all API endpoints tested E2E, Vite build passes (182KB JS).
Run from: `projects/trendforum/` — `npm run dev` starts Express :3847 + Vite :5173.
Login with dev WiFi password from prisma/seed.ts.
No Docker available locally (use EC2 spot via aws skill if needed).

## Completed (v0.1.0 MVP)
- Project scaffolding, Prisma schema, Express backend, React frontend
- Full E2E verified: auth, posts, comments, votes, reports, mod, feed
- Prisma singleton refactor, README

## Next (priority order)
- [ ] Coconut integration module (poll /api/feed, post replies as special user)
- [ ] Mobile responsive polish (sidebar drawer, smaller cards on mobile)
- [ ] Search functionality (GET /api/search?q= across post titles/bodies)
- [ ] Production hardening (CSP headers, error boundaries, bcrypt cost tuning)
- [ ] Image upload support (S3 or local storage)
- [ ] GitHub publish (grobomo account — generic tool, no PII)
