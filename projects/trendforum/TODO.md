# TrendForum TODO

## Session Handoff (2026-04-26 session 6)
T027 WebSocket done in worktree `trendforum-t027-websocket` (branch `worktree-trendforum-t027-websocket`).
Pushed to grobomo/trendforum. 4 commits: ws.ts hub, client useWebSocket hook, broadcasts in posts/comments/votes, vite proxy.
E2E verified: 3/3 event types (new_post, new_comment, vote_update). Vite build 189KB, tsc clean.
Branch needs merging to main. Worktree .git file was fixed (UNC path -> relative).
Login: WiFi="demo2026", Admin="admin2026". Run: `npm run dev` (Express :3847 + Vite :5173).
Note: old worktrees `trendforum-build` and `trendforum-scaffold` are prunable — can be cleaned up.

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
- T027: WebSocket real-time updates — ws server, broadcast on post/comment/vote, client useWebSocket hook, live feeds + post detail. E2E 3/3 event types verified. Vite build 189KB, tsc clean.

## Next (priority order)
- [ ] Merge T027 branch to main (worktree-trendforum-t027-websocket -> main)
- [ ] T028: Notification badges for unread activity
- [ ] T029: Rate-limit WebSocket connections per IP
- [ ] Clean up prunable worktrees (trendforum-build, trendforum-scaffold)
