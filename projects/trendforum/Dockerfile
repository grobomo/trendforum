FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --ignore-scripts

COPY . .
RUN npx prisma generate
RUN npm run build

RUN mkdir -p data

EXPOSE 3847

CMD ["sh", "-c", "npx prisma db push --skip-generate && npm start"]
