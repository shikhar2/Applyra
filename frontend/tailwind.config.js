/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          900: '#1e3a8a',
        },
        surface: {
          50:  'rgba(255,255,255,0.06)',
          100: 'rgba(255,255,255,0.08)',
          200: 'rgba(255,255,255,0.10)',
          300: 'rgba(255,255,255,0.14)',
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-mesh':
          'radial-gradient(at 40% 20%, rgba(99,102,241,0.18) 0px, transparent 50%), radial-gradient(at 80% 0%, rgba(59,130,246,0.12) 0px, transparent 50%), radial-gradient(at 0% 50%, rgba(139,92,246,0.10) 0px, transparent 50%)',
      },
      boxShadow: {
        'glass':   '0 4px 24px 0 rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.06)',
        'glass-lg':'0 8px 40px 0 rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.08)',
        'glow-blue':  '0 0 20px rgba(59,130,246,0.35)',
        'glow-purple':'0 0 20px rgba(139,92,246,0.35)',
        'glow-green': '0 0 20px rgba(34,197,94,0.30)',
        'card-3d':    '0 20px 60px rgba(0,0,0,0.6), 0 4px 12px rgba(0,0,0,0.4)',
        'inner-glow': 'inset 0 1px 0 rgba(255,255,255,0.1)',
      },
      backdropBlur: {
        xs: '2px',
      },
      animation: {
        'float':        'float 6s ease-in-out infinite',
        'pulse-slow':   'pulse 4s cubic-bezier(0.4,0,0.6,1) infinite',
        'shimmer':      'shimmer 2.5s linear infinite',
        'spin-slow':    'spin 8s linear infinite',
        'glow':         'glow 3s ease-in-out infinite alternate',
        'slide-up':     'slideUp 0.4s ease-out',
        'fade-in':      'fadeIn 0.3s ease-out',
      },
      keyframes: {
        float: {
          '0%,100%': { transform: 'translateY(0px)' },
          '50%':     { transform: 'translateY(-8px)' },
        },
        shimmer: {
          '0%':   { backgroundPosition: '-200% center' },
          '100%': { backgroundPosition: '200% center' },
        },
        glow: {
          '0%':   { boxShadow: '0 0 10px rgba(59,130,246,0.2)' },
          '100%': { boxShadow: '0 0 30px rgba(59,130,246,0.6)' },
        },
        slideUp: {
          '0%':   { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
