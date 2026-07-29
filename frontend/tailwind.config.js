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
        'primary': 'var(--bg-primary)',
        'secondary': 'var(--bg-secondary)',
        'bg-primary': 'var(--bg-primary)',
        'bg-secondary': 'var(--bg-secondary)',
        'bg-tertiary': 'var(--bg-tertiary)',
        'bg-elevated': 'var(--bg-elevated)',
        'primary-text': 'var(--text-primary)',
        'secondary-text': 'var(--text-secondary)',
        'muted': 'var(--text-muted)',
        'charcoal-dark': 'var(--bg-secondary)',
        charcoal: {
          light: 'var(--bg-elevated)',
          DEFAULT: 'var(--bg-tertiary)',
          dark: 'var(--bg-primary)', /* mapped for backward compatibility */
        },
        'silver-bright': 'var(--accent-silver-bright)',
        silver: {
          bright: 'var(--accent-silver-bright)',
          DEFAULT: 'var(--accent-silver)',
          dark: 'var(--text-muted)',
        },
        rag: {
          red: 'var(--rag-red)',
          amber: 'var(--rag-amber)',
          'amber-bright': '#fbbf24',   
          green: 'var(--rag-green)',
          blue: 'var(--rag-blue)',
          'blue-bright': '#3b82f6',    
        },
        accent: {
          silver: 'var(--accent-silver)',
          'silver-bright': 'var(--accent-silver-bright)',
          'silver-dim': 'var(--accent-silver-dim)',
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
