# TrendForum - Build Plan

## T001: Build Forum Application

Building anonymous Reddit-like forum for Trend Micro employees per ARCHITECTURE.md.

### Tasks
- [x] T001 Project scaffolding (package.json, tsconfig, vite, tailwind, docker) — DONE: config files committed
- [ ] T002 Prisma schema and seed data — scaffold schema.prisma with all models from ARCHITECTURE.md, seed default subforums and test passwords
- [ ] T003 Server entry point and middleware (auth, rate-limit) — Express server on :3847, JWT auth, bcrypt WiFi password verify, rate limiting by JTI
- [ ] T004 API routes (auth, subforums, posts, comments, votes, reports, mod, feed) — all REST endpoints per ARCHITECTURE.md 4.4
- [ ] T005 Frontend app shell (routing, auth context, API client) — React Router, auth context with localStorage token, fetch wrapper
- [ ] T006 Frontend components (login, feeds, post detail, comments, submit form) — full Reddit-like UI with Tailwind
- [ ] T007 npm install, prisma generate, seed, verify dev server
- [ ] T008 Dockerfile and docker-compose.yml for single-command deploy
