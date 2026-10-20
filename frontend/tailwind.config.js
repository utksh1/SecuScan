/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'primary': 'color-mix(in srgb, var(--bg-primary) 100%, transparent)',
        'secondary': 'color-mix(in srgb, var(--bg-secondary) 100%, transparent)',
        'bg-primary': 'color-mix(in srgb, var(--bg-primary) 100%, transparent)',
        'bg-secondary': 'color-mix(in srgb, var(--bg-secondary) 100%, transparent)',
        'bg-tertiary': 'color-mix(in srgb, var(--bg-tertiary) 100%, transparent)',
        'bg-elevated': 'color-mix(in srgb, var(--bg-elevated) 100%, transparent)',
        'primary-text': 'color-mix(in srgb, var(--text-primary) 100%, transparent)',
        'secondary-text': 'color-mix(in srgb, var(--text-secondary) 100%, transparent)',
        'muted': 'color-mix(in srgb, var(--text-muted) 100%, transparent)',
        'charcoal-dark': 'color-mix(in srgb, var(--bg-primary) 100%, transparent)',
        charcoal: {
          light: 'color-mix(in srgb, var(--bg-tertiary) 100%, transparent)',
          DEFAULT: 'color-mix(in srgb, var(--bg-secondary) 100%, transparent)',
          dark: 'color-mix(in srgb, var(--bg-primary) 100%, transparent)', /* mapped for backward compatibility */
        },
        silver: {
          bright: 'color-mix(in srgb, var(--text-primary) 100%, transparent)',
          DEFAULT: 'color-mix(in srgb, var(--text-secondary) 100%, transparent)',
          dark: 'color-mix(in srgb, var(--text-muted) 100%, transparent)',
        },
        rag: {
          red: '#ef4444',
          amber: '#f59e0b',
          'amber-bright': '#fbbf24',   
          green: '#10b981',
          blue: '#1e88e5',
          'blue-bright': '#3b82f6',    
        },
        accent: {
          silver: 'color-mix(in srgb, var(--accent-silver) 100%, transparent)'
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
