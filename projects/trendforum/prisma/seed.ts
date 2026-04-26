import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcryptjs';

const prisma = new PrismaClient();

async function main() {
  const wifiHash = await bcrypt.hash('demo2026', 10);
  const adminHash = await bcrypt.hash('admin2026', 10);

  await prisma.config.upsert({
    where: { key: 'wifi_password_hash' },
    update: { value: wifiHash },
    create: { key: 'wifi_password_hash', value: wifiHash },
  });

  await prisma.config.upsert({
    where: { key: 'admin_password_hash' },
    update: { value: adminHash },
    create: { key: 'admin_password_hash', value: adminHash },
  });

  const subforums = [
    { slug: 'general', name: 'General', description: 'General discussion for all Trenders' },
    { slug: 'engineering', name: 'Engineering', description: 'Software engineering, architecture, and tech discussions' },
    { slug: 'product-feedback', name: 'Product Feedback', description: 'Ideas and feedback on Trend Micro products' },
    { slug: 'random', name: 'Random', description: 'Off-topic conversations, memes, and fun stuff' },
    { slug: 'career', name: 'Career', description: 'Career growth, interviews, and professional development' },
    { slug: 'announcements', name: 'Announcements', description: 'Company-wide announcements and news' },
    { slug: 'security-research', name: 'Security Research', description: 'Threat research, CVEs, and security topics' },
    { slug: 'watercooler', name: 'Water Cooler', description: 'Casual chat — what are you up to today?' },
  ];

  for (const sf of subforums) {
    await prisma.subforum.upsert({
      where: { slug: sf.slug },
      update: {},
      create: sf,
    });
  }
  console.log(`Seeded ${subforums.length} subforums`);

  // Example posts
  const general = await prisma.subforum.findUnique({ where: { slug: 'general' } });
  const random = await prisma.subforum.findUnique({ where: { slug: 'random' } });

  if (general) {
    await prisma.post.upsert({
      where: { id: 1 },
      update: {},
      create: {
        subforumId: general.id,
        title: 'Welcome to TrendForum!',
        body: 'This is a safe, anonymous space for Trenders to discuss anything. No one can see who you are — not even admins. Be honest, be respectful, and have fun.',
        score: 5,
      },
    });
  }

  if (random) {
    await prisma.post.upsert({
      where: { id: 2 },
      update: {},
      create: {
        subforumId: random.id,
        title: 'What are you listening to right now?',
        body: 'Drop your current playlist or song recommendation. Need new music.',
        score: 3,
      },
    });
  }

  console.log('Seed complete. Dev passwords: WiFi="demo2026", Admin="admin2026"');
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
