import type { Config } from 'tailwindcss';

export default {
  darkMode: ['class'],
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './providers/**/*.{ts,tsx}',
    './store/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        ink: '#0f172a',
        panel: '#111827',
        muted: '#6b7280',
        accent: '#2563eb',
      },
      boxShadow: {
        soft: '0 12px 32px rgba(15, 23, 42, 0.18)',
      },
    },
  },
  plugins: [],
} satisfies Config;
