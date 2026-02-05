/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Refined editorial palette
        ink: {
          50: '#f8f9fa',
          100: '#f1f3f5',
          200: '#e9ecef',
          300: '#dee2e6',
          400: '#ced4da',
          500: '#adb5bd',
          600: '#868e96',
          700: '#495057',
          800: '#343a40',
          900: '#212529',
          950: '#0d1117',
        },
        // Status colors - muted but clear
        status: {
          beta: '#6366f1',      // Indigo - something new
          preview: '#8b5cf6',   // Violet - experimental
          optional: '#0ea5e9',  // Sky - available
          released: '#10b981',  // Emerald - stable
          deprecated: '#f59e0b', // Amber - caution
          pending: '#64748b',   // Slate - waiting
        },
        // Accent
        accent: {
          primary: '#2563eb',   // Blue
          warm: '#ea580c',      // Orange
        },
        // Canvas brand colors (kept for reference)
        canvas: {
          primary: '#0374B5',
          secondary: '#394B58',
          success: '#0B874B',
          warning: '#BF4D00',
          danger: '#D64242',
          light: '#F5F5F5',
        }
      },
      fontFamily: {
        'display': ['"Source Serif 4"', 'Georgia', 'serif'],
        'body': ['"DM Sans"', 'system-ui', 'sans-serif'],
        'mono': ['"JetBrains Mono"', 'monospace'],
      },
      fontSize: {
        'display-lg': ['2.5rem', { lineHeight: '1.1', letterSpacing: '-0.02em' }],
        'display': ['2rem', { lineHeight: '1.2', letterSpacing: '-0.015em' }],
        'display-sm': ['1.5rem', { lineHeight: '1.25', letterSpacing: '-0.01em' }],
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.5s ease-out',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
      },
      boxShadow: {
        'card': '0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06)',
        'card-hover': '0 4px 12px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.06)',
        'elevated': '0 10px 40px rgba(0,0,0,0.08)',
      },
    },
  },
  plugins: [],
}
