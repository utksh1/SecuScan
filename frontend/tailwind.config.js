/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
  // Dynamic theme colors from CSS variables
  'charcoal-dark': 'var(--bg-primary)',

  charcoal: {
    light: 'var(--bg-tertiary)',
    DEFAULT: 'var(--bg-secondary)',
    dark: 'var(--bg-elevated)',
  },

  // Better adaptive text colors
 silver: {
  bright: 'var(--text-primary)',
  DEFAULT: 'var(--text-secondary)',
  dark: '#111827',
},

  // Status colors
  rag: {
    red: '#ef4444',
    amber: '#f59e0b',
    'amber-bright': '#fbbf24',
    green: '#10b981',
    blue: '#2563eb',
    'blue-bright': '#3b82f6',
  },

  // Accent system
  accent: {
    silver: 'var(--accent-silver)',
    dim: 'var(--accent-silver-dim)',
    bright: 'var(--accent-silver-bright)',
  },

  // Extra UI utility colors
  panel: {
    bg: 'var(--bg-secondary)',
    elevated: 'var(--bg-elevated)',
    border: 'rgba(0,0,0,0.15)',
  }
},
      fontFamily: {
        mono: ['"IBM Plex Mono"', 'Menlo', 'monospace'],
        sans: ['"Inter"', 'system-ui', 'sans-serif'],
        serif: ['"Playfair Display"', 'Georgia', 'serif'],    
      },
      animation: {
        'fast-pulse': 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'snake': 'snake 2s linear infinite',
        'fade-in': 'fadeIn 0.5s ease-out',
        'glitch': 'glitch 1s infinite alternate',
      },
      keyframes: {
        snake: {
          '0%': { backgroundPosition: '0% 50%' },
          '100%': { backgroundPosition: '100% 50%' }
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' }
        },
        glitch: {
            '0%': { transform: 'translate(0)' },
            '20%': { transform: 'translate(-2px, 2px)' },
            '40%': { transform: 'translate(-2px, -2px)' },
            '60%': { transform: 'translate(2px, 2px)' },
            '80%': { transform: 'translate(2px, -2px)' },
            '100%': { transform: 'translate(0)' }
        }
      }
    },
  },
  plugins: [],
}
