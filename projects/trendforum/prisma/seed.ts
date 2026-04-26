import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcryptjs';

const prisma = new PrismaClient();

async function main() {
  const wifiHash = await bcrypt.hash('trender2026', 10);
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
    { slug: 'engineering', name: 'Engineering', description: 'Code, architecture, and tech talk' },
    { slug: 'product-feedback', name: 'Product Feedback', description: 'Ideas and feedback on our products' },
    { slug: 'random', name: 'Random', description: 'Off-topic, memes, and fun' },
    { slug: 'announcements', name: 'Announcements', description: 'Company-wide announcements' },
    { slug: 'career', name: 'Career', description: 'Career growth, mentoring, and job advice' },
  ];

  for (const sf of subforums) {
    await prisma.subforum.upsert({
      where: { slug: sf.slug },
      update: {},
      create: sf,
    });
  }

  console.log('Seed complete. Dev passwords: WiFi="trender2026", Admin="admin2026"');
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
