# TrendForum TODO

## Session Handoff (2026-04-26 session 5)
Working in worktree `trendforum-build` on branch `001-T001-create-forum-app`.
Published to grobomo/trendforum (public). Login: WiFi="demo2026", Admin="admin2026".
Run: `npm run dev` (Express :3847 + Vite :5173).
E2E scripts: `bash test-coconut.sh` (7/7), `bash test-upload.sh` (5/5).
Note: test scripts use demo2026 password, db must be re-seeded after schema change (T012).
Published to grobomo/trendforum (public). Vite build: 264KB JS. All 3 E2E suites pass.
Publish workflow: edit in worktree, patch to /tmp/tmp.F3IMnHJEQV, push via gh_auto.

## Completed
- v0.1.0 MVP: scaffolding, Prisma, Express, React, auth, posts, comments, votes, reports, mod, feed, search
- Security headers, Prisma singleton refactor, README
- Coconut bot: poll feed, reply as "Coconut", admin API, 7/7 E2E
- Mobile responsive: hamburger drawer, collapsible search, compact cards
- Error boundaries: ErrorBoundary wrapping App + Layout content
- Image upload: multer, local storage, 5MB limit, JPEG/PNG/GIF/WebP, 5/5 E2E
- Fixed TS error in comments route
- T010: GitHub publish — genericized (member/Anon-XXX), MIT license, secret-scan CI, grobomo/trendforum
- T011: Coconut LLM integration — claude -p with template fallback, async replies
- T012: User profiles — pseudonyms, profile pages at /u/:name, "Claim ID" modal in header
- T013: Pagination UI — prev/next on HomeFeed and SubforumFeed, page in URL params

- T014: E2E test — profiles 10/10, upload 5/5, coconut 7/7 all pass
- T015: Hardening — input length limits, type checks, apiLimiter on all routes
- T016: Markdown rendering — marked + DOMPurify, Tailwind typography
- T017: Admin dashboard UI — moderation queue at /admin with remove actions

- T018: README rewritten with full feature list, API reference, E2E test docs
- T019: PostCard markdown preview in feed cards

- T020: Vite build verified — 264KB JS, server TS build clean
- T021: Docker fixed — npm install, DB init on startup, uploads volume
- T022: Clickable pseudonyms in comments — link to /u/:name
- T023: Drop profile — "Drop ID" button, POST /api/profile/drop

- T024: Deps verified in grobomo repo (marked, dompurify, typography all present)
- T025: Final E2E — all 3 suites pass: upload 5/5, coconut 7/7, profile 10/10

- T026: Dark/light theme toggle — CSS variables, 218 color migrations, localStorage

## Next (priority order)
- [ ] T027: WebSocket for real-time post/comment updates
