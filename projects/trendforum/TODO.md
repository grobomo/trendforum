# TrendForum TODO

## Session Handoff (2026-04-26 session 3)
Working in worktree `trendforum-build` on branch `001-T001-create-forum-app`.
PR #1 open at joel-ginsberg_tmemu/coconut-workspace. Zero TS errors. Vite build: 188KB JS.
Run: `npm run dev` (Express :3847 + Vite :5173). Login: WiFi="trender2026", Admin="admin2026".
E2E scripts: `bash test-coconut.sh` (7/7), `bash test-upload.sh` (5/5).
NOTE: Session CWD may be in commit-t009 worktree — exit it first.

## Completed
- v0.1.0 MVP: scaffolding, Prisma, Express, React, auth, posts, comments, votes, reports, mod, feed, search
- Security headers, Prisma singleton refactor, README
- Coconut bot: poll feed, reply as "Coconut", admin API, 7/7 E2E (PR #1)
- Mobile responsive: hamburger drawer, collapsible search, compact cards (PR #1)
- Error boundaries: ErrorBoundary wrapping App + Layout content (PR #1)
- Image upload: multer, local storage, 5MB limit, JPEG/PNG/GIF/WebP, 5/5 E2E (PR #1)
- Fixed TS error in comments route (PR #1)

- T027: WebSocket real-time updates — ws server, broadcast on post/comment/vote, client useWebSocket hook, live feeds + post detail. E2E verified: 3/3 event types.
- T010: GitHub publish — live at https://github.com/grobomo/trendforum (public, PII-free, 2026-04-27)
- T011: Coconut LLM integration — Anthropic SDK + Claude Haiku replies, graceful fallback to templates (2026-04-27)
- T012: User profiles / persistent identity — clickable usernames in comments, public profile pages with comment history + stats, profile comments API (2026-04-27)
- T028: Notification badges — Prisma Notification model, /api/notifications routes (list/count/mark-read), reply notifications on comment creation, real-time push via WebSocket (profileId-targeted), NotificationBell dropdown in header (2026-04-27)

## Next (priority order)
- [ ] T029: Rate-limit WebSocket connections per IP
- [ ] T030: Polish notification UX (notification page, clear individual, notification sounds)
