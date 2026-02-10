/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Dark ops console palette
        surface: {
          0: '#0a0a0b',
          1: '#111113',
          2: '#18181b',
          3: '#1f1f23',
          4: '#27272a',
        },
        zinc: {
          50: '#fafafa',
          100: '#f4f4f5',
          200: '#e4e4e7',
          300: '#d4d4d8',
          400: '#a1a1aa',
          500: '#71717a',
          600: '#52525b',
          700: '#3f3f46',
          800: '#27272a',
          900: '#18181b',
          950: '#09090b',
        },
        // Signal colors - vivid against dark
        signal: {
          green: '#22c55e',
          blue: '#3b82f6',
          violet: '#8b5cf6',
          amber: '#f59e0b',
          red: '#ef4444',
          cyan: '#06b6d4',
          slate: '#64748b',
        },
        // Status mapping
        status: {
          beta: '#818cf8',      // Indigo-400
          preview: '#a78bfa',   // Violet-400
          optional: '#38bdf8',  // Sky-400
          released: '#4ade80',  // Green-400
          deprecated: '#fbbf24', // Amber-400
          pending: '#94a3b8',   // Slate-400
        },
      },
      fontFamily: {
        'sans': ['"Geist"', 'system-ui', '-apple-system', 'sans-serif'],
        'mono': ['"Geist Mono"', '"JetBrains Mono"', 'monospace'],
      },
      fontSize: {
        'metric': ['2rem', { lineHeight: '1', letterSpacing: '-0.04em', fontWeight: '600' }],
        'title': ['1.25rem', { lineHeight: '1.3', letterSpacing: '-0.02em', fontWeight: '600' }],
        'label': ['0.8125rem', { lineHeight: '1', letterSpacing: '0.04em', fontWeight: '500' }],
      },
      boxShadow: {
        'glow-green': '0 0 20px rgba(34,197,94,0.15)',
        'glow-amber': '0 0 20px rgba(245,158,11,0.15)',
        'glow-red': '0 0 20px rgba(239,68,68,0.15)',
        'glow-blue': '0 0 20px rgba(59,130,246,0.15)',
        'glow-violet': '0 0 20px rgba(139,92,246,0.15)',
        'card': '0 1px 2px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.03)',
        'card-hover': '0 4px 12px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.06)',
        'elevated': '0 8px 30px rgba(0,0,0,0.7)',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-dot': 'pulseDot 2s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseDot: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.4' },
        },
        glow: {
          '0%': { opacity: '0.5' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
