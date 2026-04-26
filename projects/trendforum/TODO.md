# TrendForum TODO

## Session Handoff (2026-04-26 session 2)
Working in worktree `trendforum-build` on branch `001-T001-create-forum-app`.
PR #1 open at joel-ginsberg_tmemu/coconut-workspace.
Run from: `projects/trendforum/` — `npm run dev` starts Express :3847 + Vite :5173.
Login: WiFi="trender2026", Admin="admin2026". Zero TypeScript errors. Vite build: 186KB JS.
Coconut bot: `POST /api/coconut/start` (admin token). E2E: `bash test-coconut.sh`.

## Completed
- v0.1.0 MVP: scaffolding, Prisma schema, Express backend, React frontend
- Full E2E verified: auth, posts, comments, votes, reports, mod, feed, search
- Prisma singleton refactor, README, security headers
- Coconut bot: poll feed, reply as "Coconut", admin API, 7/7 E2E (PR #1)
- Mobile responsive: hamburger drawer, collapsible search, compact cards (PR #1)
- Error boundaries: ErrorBoundary component wrapping App + Layout content (PR #1)
- Fixed pre-existing TS error in comments route (PR #1)

## Next (priority order)
- [ ] T009: Image upload support (S3 or local storage)
- [ ] T010: GitHub publish (grobomo account — generic tool, no PII)
- [ ] T011: Coconut LLM integration — swap template replies for Claude API calls
- [ ] T012: User profiles / persistent identity across sessions
- [ ] T013: Pagination UI (next/prev buttons on feeds)
