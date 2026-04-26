import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/client/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        trend: {
          red: '#D5232F',
          dark: '#1a1a2e',
          darker: '#16162a',
          card: '#1e1e3a',
          border: '#2a2a4a',
          text: '#e0e0e0',
          muted: '#8888aa',
        },
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
} satisfies Config;
