/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // xCloud 品牌紅 — 取自 Logo #C41230
        brand: {
          50:  '#fff1f2',
          100: '#ffe0e3',
          200: '#ffc5cb',
          300: '#ff97a2',
          400: '#ff5a6b',
          500: '#e8112a',
          600: '#c41230',   // Logo 主色
          700: '#9e0f27',
          800: '#7d1021',
          900: '#63101d',
          950: '#37060f',
        },
        // Sidebar — 近黑炭色，帶 xCloud 質感
        sidebar:         '#111116',
        'sidebar-hover': '#1c1c24',
        'sidebar-active':'rgba(196,18,48,0.18)',
      },
      fontFamily: {
        sans: ['"Inter"', '"Noto Sans TC"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      boxShadow: {
        'card':       '0 1px 3px 0 rgba(0,0,0,.08), 0 1px 2px -1px rgba(0,0,0,.06)',
        'card-hover': '0 4px 16px 0 rgba(0,0,0,.14), 0 2px 4px -2px rgba(0,0,0,.10)',
        'red-glow':   '0 0 24px -4px rgba(196,18,48,.35)',
      },
      animation: {
        'fade-in':    'fadeIn 0.22s ease-out',
        'slide-up':   'slideUp 0.28s ease-out',
        'pulse-slow': 'pulse 3s infinite',
      },
      keyframes: {
        fadeIn:  { from: { opacity: 0 },                               to: { opacity: 1 } },
        slideUp: { from: { opacity: 0, transform: 'translateY(10px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
      },
    },
  },
  plugins: [],
}
