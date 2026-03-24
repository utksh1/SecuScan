/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        charcoal: {
          light: '#2a2d34',
          DEFAULT: '#1a1c23',
          dark: '#0f1115',
        },
        silver: {
          bright: '#e2e8f0',
          DEFAULT: '#94a3b8',
          dark: '#475569',
        },
        rag: {
          red: '#ff3366',
          amber: '#ffaa00',
          'amber-bright': '#ffcc00',   
          green: '#00e676',
          blue: '#1e88e5',
          'blue-bright': '#42a5f5',    
        },
        accent: {
          silver: '#cbd5e1'
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
