import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/client/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        page: 'var(--bg-page)',
        header: 'var(--bg-header)',
        card: 'var(--bg-card)',
        input: 'var(--bg-input)',
        border: 'var(--border)',
        'border-hover': 'var(--border-hover)',
        text: 'var(--text)',
        muted: 'var(--text-muted)',
        dim: 'var(--text-dim)',
        accent: 'var(--accent)',
        'accent-hover': 'var(--accent-hover)',
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
} satisfies Config;
