# TrendForum Build

## T001: Build Forum Application
- [x] Create spec (specs/build-forum/spec.md)
- [x] Project scaffolding (package.json, configs, docker)
- [ ] T002: Prisma schema + seed — DONE, needs PR
- [ ] T003: Express backend — DONE, needs PR
- [ ] T004: API routes — DONE, needs PR
- [ ] T005: React frontend — DONE, needs PR
- [ ] T006: Frontend components — DONE, needs PR
- [ ] T007: Integration — DONE, needs PR

## Verified
- Server starts on port 3847
- Auth endpoint returns JWT for correct WiFi password
- 6 subforums seeded (see prisma/seed.ts for dev credentials)
- Full E2E: auth, subforums, posts, comments, votes, feed, reports, mod all pass
- Vite build: 45 modules, 182KB JS + 11KB CSS
- Prisma singleton refactor: shared db.ts across all routes

## Next Steps
- [ ] T008: Add README.md with setup instructions and screenshots
- [ ] T009: Deploy to Docker and test containerized
- [ ] T010: Add Coconut integration module (poll + reply)
- [ ] T011: Mobile responsive polish
- [ ] T012: Publish to GitHub (grobomo account — generic tool, no PII)
