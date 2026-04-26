FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npx prisma generate
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
COPY --from=builder /app/prisma ./prisma
RUN mkdir -p /app/uploads /app/data
ENV DATABASE_URL=file:/app/data/trendforum.db
EXPOSE 3847
CMD ["sh", "-c", "npx prisma db push --skip-generate && node dist/server/index.js"]
