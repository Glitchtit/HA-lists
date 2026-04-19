/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          orange:       'var(--brand-orange)',
          'orange-600': 'var(--brand-orange-600)',
          'orange-400': 'var(--brand-orange-400)',
          'orange-300': 'var(--brand-orange-300)',
          'orange-100': 'var(--brand-orange-100)',
          cobalt:       'var(--brand-cobalt)',
          'cobalt-600': 'var(--brand-cobalt-600)',
          'cobalt-400': 'var(--brand-cobalt-400)',
          'cobalt-300': 'var(--brand-cobalt-300)',
          'cobalt-100': 'var(--brand-cobalt-100)',
        },
        surface: {
          0: 'var(--bg-0)',
          1: 'var(--bg-1)',
          2: 'var(--bg-2)',
          3: 'var(--bg-3)',
          4: 'var(--bg-4)',
        },
        line: {
          1: 'var(--line-1)',
          2: 'var(--line-2)',
        },
        ink: {
          1: 'var(--fg-1)',
          2: 'var(--fg-2)',
          3: 'var(--fg-3)',
          4: 'var(--fg-4)',
        },
        semantic: {
          success: 'var(--success)',
          warning: 'var(--warning)',
          danger:  'var(--danger)',
          info:    'var(--info)',
        },
      },
      fontFamily: {
        sans:    ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        display: ['Space Grotesk', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
        body:    ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono:    ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      borderRadius: {
        xl:   '12px',
        '2xl':'16px',
      },
      boxShadow: {
        'glow-orange': '0 0 24px rgba(255, 79, 0, 0.45)',
        'glow-cobalt': '0 0 24px rgba(46, 107, 214, 0.45)',
      },
    },
  },
  plugins: [],
}
