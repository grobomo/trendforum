# Build Forum - Task Tracking

## T001 Project Scaffolding
- [ ] package.json with all dependencies
- [ ] tsconfig.json + tsconfig.server.json
- [ ] vite.config.ts with proxy to Express
- [ ] tailwind.config.ts + postcss.config.js
- [ ] Dockerfile + docker-compose.yml
- [ ] .gitignore, .env, .env.example, index.html

## T002 Database Schema
- [ ] prisma/schema.prisma (Subforum, Post, Comment, Vote, Report, ModAction, Config)
- [ ] prisma/seed.ts (default subforums + dev passwords)

## T003 Server Core
- [ ] src/server/index.ts (Express app, route mounting, static serve)
- [ ] src/server/auth.ts (JWT, bcrypt, display name generation)
- [ ] src/server/middleware/requireAuth.ts
- [ ] src/server/middleware/rateLimit.ts

## T004 API Routes
- [ ] src/server/routes/auth.ts (verify WiFi password, admin login)
- [ ] src/server/routes/subforums.ts (list subforums)
- [ ] src/server/routes/posts.ts (CRUD + hot scoring)
- [ ] src/server/routes/comments.ts (threaded comments)
- [ ] src/server/routes/votes.ts (upvote/downvote toggle)
- [ ] src/server/routes/reports.ts (content reporting)
- [ ] src/server/routes/mod.ts (moderation dashboard API)
- [ ] src/server/routes/feed.ts (Coconut integration feed)

## T005 Frontend Shell
- [ ] src/client/main.tsx (React entry)
- [ ] src/client/App.tsx (routing + auth guard)
- [ ] src/client/index.css (Tailwind directives)
- [ ] src/client/lib/api.ts (API client)
- [ ] src/client/lib/time.ts (time formatting)
- [ ] src/client/hooks/useAuth.ts (auth context)

## T006 Frontend Components
- [ ] Layout.tsx (header + sidebar + outlet)
- [ ] LoginForm.tsx (WiFi password entry)
- [ ] HomeFeed.tsx + SubforumFeed.tsx (post lists)
- [ ] SortTabs.tsx (hot/new/top)
- [ ] PostCard.tsx (feed item)
- [ ] PostDetail.tsx (full post + comment form)
- [ ] CommentTree.tsx (recursive threaded comments)
- [ ] VoteButton.tsx (up/down with score)
- [ ] SubforumSidebar.tsx (subforum nav)
- [ ] SubmitForm.tsx (new post creation)

## T007 Integration
- [ ] npm install
- [ ] prisma generate + db push + seed
- [ ] verify dev server runs
