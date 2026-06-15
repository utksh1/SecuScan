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
        'theme-dark': 'rgb(var(--tw-color-theme-dark) / <alpha-value>)',
        'theme-inverse': 'rgb(var(--tw-color-theme-inverse) / <alpha-value>)',
        'charcoal-dark': 'rgb(var(--tw-color-charcoal-dark) / <alpha-value>)',
        charcoal: {
          light: 'rgb(var(--tw-color-charcoal-light) / <alpha-value>)',
          DEFAULT: 'rgb(var(--tw-color-charcoal) / <alpha-value>)',
          dark: 'rgb(var(--tw-color-charcoal-dark) / <alpha-value>)',
        },
        silver: {
          bright: 'rgb(var(--tw-color-silver-bright) / <alpha-value>)',
          DEFAULT: 'rgb(var(--tw-color-silver) / <alpha-value>)',
          dark: 'rgb(var(--tw-color-silver-dark) / <alpha-value>)',
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
          silver: 'rgb(var(--tw-color-accent-silver) / <alpha-value>)'
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
