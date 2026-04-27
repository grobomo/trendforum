/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/client/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        forum: {
          bg: '#1a1a2e',
          card: '#262640',
          hover: '#2d2d50',
          border: '#3a3a5c',
          muted: '#8b8baf',
          accent: '#ff6b35',
          upvote: '#ff4500',
          downvote: '#7193ff',
        },
      },
    },
  },
  plugins: [],
};
