# TrendForum — Architecture & Design Document

> Anonymous community forum inspired by Reddit. No accounts, no tracking — just a shared password to prove you belong.

## 1. Problem Statement

Teams often lack a safe, anonymous channel for candid discussion across orgs. Existing tools (Teams, email, Slack) are tied to identity, which suppresses honest feedback. Reddit works for public discourse precisely because anonymity resists self-censorship.

## 2. Ideal End State (Maze Principle — work backward from the solution)

A user opens TrendForum on their browser. They enter the current shared community password. No username, no email, no account creation. They land on a Reddit-like feed of posts organized by "subforum" (like subreddits). They can:
- Browse all subforums or filter by one
- Post text, links, or images anonymously
- Comment on posts, reply to comments (threaded)
- Upvote/downvote posts and comments
- See post scores, sort by hot/new/top
- Report content (mod queue, not public)

No one — not even admins — can link a post to a specific person.

## 3. Core Requirements

1. **Anonymous auth via monthly rotating BYOD WiFi password** — proves you're a Trender without revealing who you are
2. **No logs** of user identity — sessions are ephemeral, no IP logging, no tracking cookies
3. **Open source** — full transparency, trust through code
4. **UX-focused** — clean Reddit-like experience, not a corporate tool
5. **Subforum-level filtering and moderation** — subreddit-like structure
6. **Coconut monitoring** — like Teams/GitHub/Slack monitoring, Coconut can watch posts and respond
7. **Future customer-facing version** — architecture should support multi-tenant deployment

## 4. Architecture

### 4.1 Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | React 18 + TypeScript | Modern, fast, huge ecosystem |
| UI Framework | Tailwind CSS + shadcn/ui | Reddit-like aesthetic, customizable |
| Backend | Node.js + Express + TypeScript | Same language as frontend, fast dev |
| Database | SQLite (dev) → PostgreSQL (prod) | Zero-config dev, scalable prod |
| ORM | Prisma | Type-safe DB access, migrations |
| Auth | Shared-secret (WiFi password) → session token | No identity, just access proof |
| Deployment | Docker Compose | Single-command deploy |

### 4.2 Privacy-First Design

```
User enters WiFi password → Server validates against current month's hash
                          → Server issues anonymous session token (JWT, no user ID)
                          → Token contains: { role: "trender", exp: 24h, jti: random }
                          → No IP logged, no fingerprinting, no analytics
```

**Key privacy decisions:**
- Session tokens contain NO user identifier — just a random `jti` and expiry
- Server logs write to `/dev/null` in production (or structured logs with no IP/UA)
- Database stores posts/comments with auto-increment IDs only — no author field
- Each post gets a random per-thread display name (e.g., "Trender-A7x") scoped to that post's comment tree only — so you can follow a conversation but can't correlate across posts
- Rate limiting by token `jti` (per-session), not by IP

### 4.3 Data Model

```prisma
model Subforum {
  id          Int       @id @default(autoincrement())
  slug        String    @unique  // e.g., "engineering", "random", "product-feedback"
  name        String
  description String?
  createdAt   DateTime  @default(now())
  posts       Post[]
}

model Post {
  id          Int       @id @default(autoincrement())
  subforumId  Int
  subforum    Subforum  @relation(fields: [subforumId], references: [id])
  title       String
  body        String?   // text or markdown
  linkUrl     String?   // link posts
  score       Int       @default(0)
  createdAt   DateTime  @default(now())
  comments    Comment[]
  votes       Vote[]
  reports     Report[]
}

model Comment {
  id          Int       @id @default(autoincrement())
  postId      Int
  post        Post      @relation(fields: [postId], references: [id])
  parentId    Int?      // threaded replies
  parent      Comment?  @relation("CommentThread", fields: [parentId], references: [id])
  children    Comment[] @relation("CommentThread")
  displayName String    // random per-post-tree, e.g., "Trender-K9m"
  body        String
  score       Int       @default(0)
  createdAt   DateTime  @default(now())
  votes       Vote[]
  reports     Report[]
}

model Vote {
  id        Int      @id @default(autoincrement())
  tokenJti  String   // session token jti — prevents double-voting per session
  postId    Int?
  post      Post?    @relation(fields: [postId], references: [id])
  commentId Int?
  comment   Comment? @relation(fields: [commentId], references: [id])
  value     Int      // +1 or -1
  @@unique([tokenJti, postId])
  @@unique([tokenJti, commentId])
}

model Report {
  id        Int      @id @default(autoincrement())
  postId    Int?
  post      Post?    @relation(fields: [postId], references: [id])
  commentId Int?
  comment   Comment? @relation(fields: [commentId], references: [id])
  reason    String
  createdAt DateTime @default(now())
}

model ModAction {
  id        Int      @id @default(autoincrement())
  action    String   // "remove_post", "remove_comment", "lock_post"
  targetId  Int
  targetType String  // "post" or "comment"
  reason    String?
  createdAt DateTime @default(now())
}

model Config {
  key   String @id
  value String
  // Stores: current_wifi_password_hash, password_rotation_date, etc.
}
```

### 4.4 API Endpoints

```
Auth:
  POST   /api/auth/verify          { password } → { token }

Subforums:
  GET    /api/subforums             → list all subforums

Posts:
  GET    /api/subforums/:slug/posts?sort=hot|new|top&page=1
  POST   /api/posts                 { subforumId, title, body?, linkUrl? }
  GET    /api/posts/:id             → post + comments tree

Comments:
  POST   /api/posts/:id/comments    { body, parentId? }

Votes:
  POST   /api/vote                  { postId?, commentId?, value: 1|-1 }

Reports:
  POST   /api/report                { postId?, commentId?, reason }

Moderation (admin password):
  GET    /api/mod/reports
  POST   /api/mod/action            { action, targetId, targetType, reason? }

Coconut Integration:
  GET    /api/feed?since=<iso>       → new posts/comments since timestamp (for polling)
  POST   /api/posts/:id/comments     → Coconut can reply to posts
```

### 4.5 Frontend Routes

```
/                          → Home feed (all subforums, hot sort)
/t/:slug                   → Subforum feed
/t/:slug/post/:id          → Post detail + comments
/t/:slug/submit            → New post form
/login                     → WiFi password entry
/mod                       → Moderation dashboard (admin)
```

### 4.6 Scoring Algorithm (Reddit "Hot" inspired)

```typescript
function hotScore(upvotes: number, downvotes: number, createdAt: Date): number {
  const score = upvotes - downvotes;
  const order = Math.log10(Math.max(Math.abs(score), 1));
  const sign = score > 0 ? 1 : score < 0 ? -1 : 0;
  const seconds = (createdAt.getTime() - new Date('2026-01-01').getTime()) / 1000;
  return sign * order + seconds / 45000;
}
```

### 4.7 Coconut Integration

Coconut monitors TrendForum the same way it monitors Teams, GitHub, and Slack:
- **Poll interval:** Every 5 minutes via `/api/feed?since=<last_check>`
- **Actions:** Can reply to posts, answer questions, share relevant KB links
- **Identity:** Posts as "🥥 Coconut" (special display name, clearly AI)
- **No moderation power** — Coconut participates but doesn't moderate

### 4.8 Deployment

```yaml
# docker-compose.yml
services:
  trendforum:
    build: .
    ports:
      - "3847:3847"
    environment:
      - DATABASE_URL=file:./data/trendforum.db
      - WIFI_PASSWORD_HASH=${WIFI_PASSWORD_HASH}
      - ADMIN_PASSWORD_HASH=${ADMIN_PASSWORD_HASH}
      - JWT_SECRET=${JWT_SECRET}
    volumes:
      - ./data:/app/data
```

## 5. Security Considerations

- **No identity storage** — the fundamental guarantee
- **Password hashing** — WiFi password stored as bcrypt hash, compared server-side
- **JWT tokens** — short-lived (24h), contain no PII
- **CSRF protection** — SameSite cookies + CSRF tokens
- **Rate limiting** — per session token, not per IP
- **Content moderation** — report system + admin dashboard
- **Open source** — anyone can audit the privacy guarantees

## 6. Multi-Tenant Future (Customer-Facing)

Architecture supports future multi-tenant mode:
- Each tenant gets their own subforum namespace
- Separate auth secrets per tenant
- Same privacy guarantees
- Tenant admin dashboard

## 7. Project Structure

```
trendforum/
├── package.json
├── tsconfig.json
├── docker-compose.yml
├── Dockerfile
├── prisma/
│   └── schema.prisma
├── src/
│   ├── server/
│   │   ├── index.ts          # Express app entry
│   │   ├── auth.ts           # WiFi password verification + JWT
│   │   ├── routes/
│   │   │   ├── auth.ts
│   │   │   ├── subforums.ts
│   │   │   ├── posts.ts
│   │   │   ├── comments.ts
│   │   │   ├── votes.ts
│   │   │   ├── reports.ts
│   │   │   ├── mod.ts
│   │   │   └── feed.ts       # Coconut integration
│   │   └── middleware/
│   │       ├── rateLimit.ts
│   │       └── requireAuth.ts
│   └── client/
│       ├── index.html
│       ├── main.tsx
│       ├── App.tsx
│       ├── components/
│       │   ├── Layout.tsx
│       │   ├── PostCard.tsx
│       │   ├── PostDetail.tsx
│       │   ├── CommentTree.tsx
│       │   ├── VoteButton.tsx
│       │   ├── SubforumSidebar.tsx
│       │   ├── SubmitForm.tsx
│       │   └── LoginForm.tsx
│       ├── hooks/
│       │   ├── useAuth.ts
│       │   └── usePosts.ts
│       └── lib/
│           └── api.ts
├── ARCHITECTURE.md
└── README.md
```
