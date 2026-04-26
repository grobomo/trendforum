# Spec: Build TrendForum

## Summary
Build an anonymous Reddit-like internal forum for Trend Micro employees.
Full architecture defined in `projects/trendforum/ARCHITECTURE.md`.

## Requirements
1. Anonymous auth via monthly rotating WiFi password (bcrypt + JWT, no user ID)
2. No identity logging - sessions are ephemeral, no IP/tracking
3. Reddit-like UX: subforums, threaded comments, voting, sorting (hot/new/top)
4. Per-post random display names (Trender-XXX) for conversation continuity
5. Content moderation via report system + admin dashboard
6. Coconut integration feed endpoint for AI monitoring
7. Docker-based deployment

## Tech Stack
- Frontend: React 18 + TypeScript + Tailwind CSS
- Backend: Node.js + Express + TypeScript
- Database: SQLite (dev) via Prisma ORM
- Auth: Shared-secret WiFi password -> JWT session token

## Scope
Single milestone: build the complete working application from ARCHITECTURE.md spec.
No multi-tenant, no production deployment - dev-ready MVP only.

## Acceptance Criteria
- [ ] `npm run dev` starts both frontend and backend
- [ ] Login with WiFi password issues anonymous JWT
- [ ] Can create posts, comments, and votes
- [ ] Threaded comment display with per-post display names
- [ ] Hot/new/top sorting works
- [ ] Moderation API functional
- [ ] Feed endpoint returns recent activity
