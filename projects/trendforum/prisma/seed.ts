import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcryptjs';

const prisma = new PrismaClient();

const subforums = [
  { slug: 'general', name: 'General', description: 'Anything and everything Trend-related' },
  { slug: 'engineering', name: 'Engineering', description: 'Code, architecture, and tech discussions' },
  { slug: 'product-feedback', name: 'Product Feedback', description: 'Feature requests, UX gripes, and product ideas' },
  { slug: 'random', name: 'Random', description: 'Off-topic, memes, water cooler chat' },
  { slug: 'wins', name: 'Wins', description: 'Celebrate victories — big and small' },
  { slug: 'gripes', name: 'Gripes', description: 'Vent safely. No names, no blame — just catharsis.' },
];

async function main() {
  console.log('🌱 Seeding TrendForum...');

  // Seed subforums
  for (const sf of subforums) {
    await prisma.subforum.upsert({
      where: { slug: sf.slug },
      update: {},
      create: sf,
    });
  }
  console.log(`  ✅ ${subforums.length} subforums seeded`);

  // Seed default WiFi password (changeme)
  const hash = await bcrypt.hash('changeme', 12);
  await prisma.config.upsert({
    where: { key: 'wifi_password_hash' },
    update: { value: hash },
    create: { key: 'wifi_password_hash', value: hash },
  });
  console.log('  ✅ Default WiFi password set (password: "changeme")');

  // Admin password
  const adminHash = await bcrypt.hash('admin-changeme', 12);
  await prisma.config.upsert({
    where: { key: 'admin_password_hash' },
    update: { value: adminHash },
    create: { key: 'admin_password_hash', value: adminHash },
  });
  console.log('  ✅ Default admin password set (password: "admin-changeme")');

  console.log('🌴 Seeding complete!');
}

main()
  .catch((e) => {
    console.error('Seeding failed:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
