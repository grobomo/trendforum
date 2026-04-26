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
- [ ] Coconut integration module (poll /api/feed, post replies as special user)
- [ ] Mobile responsive polish (sidebar drawer, smaller cards on mobile)
- [ ] Error boundaries in React for graceful failure
- [ ] Image upload support (S3 or local storage)
- [ ] GitHub publish (grobomo account — generic tool, no PII)
