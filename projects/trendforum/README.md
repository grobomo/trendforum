# TrendForum

> Anonymous internal forum for Trend Micro employees. Reddit-style, privacy-first.

## Quick Start

```bash
# Install dependencies
npm install

# Set up database + seed default subforums
npm run setup

# Start development (API + frontend with HMR)
npm run dev
```

Open **http://localhost:5173** in your browser.

Default WiFi password: `TrendForum2026`

## Architecture

- **Frontend:** React 18 + TypeScript + Vite + Tailwind CSS
- **Backend:** Node.js + Express + TypeScript
- **Database:** SQLite via Prisma ORM
- **Auth:** WiFi password → anonymous JWT (no PII)

## Privacy Guarantees

- No user identity stored anywhere
- JWT tokens contain only `jti` (random ID) and `exp` (expiry)
- No IP logging, no fingerprinting, no analytics
- Per-thread random display names (can't correlate across posts)
- Rate limiting by session token, not by IP

## Docker

```bash
# Set environment variables
export WIFI_PASSWORD="your-monthly-wifi-password"
export ADMIN_PASSWORD="mod-password"
export JWT_SECRET="change-me-in-production"

docker-compose up --build
```

Access at **http://localhost:3847**

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start dev servers (API + Vite HMR) |
| `npm run build` | Build frontend for production |
| `npm start` | Run production server |
| `npm run setup` | Generate Prisma client, push schema, seed DB |
| `npm run db:seed` | Seed default subforums |

## Default Subforums

- **general** — Open discussion
- **engineering** — Tech talk, architecture, tooling
- **product-feedback** — Feature requests & product ideas
- **random** — Off-topic, memes, whatever
- **wins** — Celebrate achievements
- **gripes** — Vent constructively

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `file:./data/trendforum.db` | SQLite database path |
| `JWT_SECRET` | `trendforum-dev-secret...` | JWT signing secret |
| `WIFI_PASSWORD` | `TrendForum2026` | Auth password |
| `ADMIN_PASSWORD` | `admin-secret-change-me` | Mod dashboard password |
| `PORT` | `3847` | API server port |
