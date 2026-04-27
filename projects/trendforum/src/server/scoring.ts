/**
 * Reddit-inspired "hot" scoring algorithm.
 * Posts with higher scores rise faster, but decay over time.
 */
export function hotScore(upvotes: number, downvotes: number, createdAt: Date): number {
  const score = upvotes - downvotes;
  const order = Math.log10(Math.max(Math.abs(score), 1));
  const sign = score > 0 ? 1 : score < 0 ? -1 : 0;
  const epoch = new Date('2026-01-01').getTime();
  const seconds = (createdAt.getTime() - epoch) / 1000;
  return sign * order + seconds / 45000;
}
