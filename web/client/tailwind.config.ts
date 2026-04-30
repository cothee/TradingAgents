import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'ta-bg': '#0f1923',
        'ta-card': '#1a2636',
        'ta-text': '#e8edf2',
        'ta-accent': '#00d4aa',
        'ta-warning': '#ffd93d',
        'ta-danger': '#ff6b6b',
        'ta-border': 'rgba(255,255,255,0.06)',
        'ta-muted': 'rgba(255,255,255,0.4)',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
        sans: ['"Noto Sans SC"', '"Source Han Sans SC"', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
} satisfies Config
