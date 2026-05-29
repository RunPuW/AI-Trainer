import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  theme: {
    extend: {
      colors: {
        ink: '#3d3d3d',
        muted: '#a6a8b3',
        canvas: '#f7f9ff',
        violet: '#9b64ff',
        indigo: '#5f79ff',
        ocean: '#4f8bff',
        orange: '#ff6b3d',
        amber: '#ff9a3d',
        coral: '#ff5b35',
        mint: '#56b878',
        butter: '#ffd86d',
        berry: '#ef8aa6',
        water: '#82bee8',
      },
      fontFamily: {
        sans: [
          'Inter',
          'PingFang SC',
          'Microsoft YaHei',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
      },
      boxShadow: {
        soft: '0 18px 55px rgba(61, 61, 61, 0.08)',
        insetNav: 'inset 0 1px 0 rgba(255, 255, 255, 0.72)',
      },
    },
  },
  plugins: [],
} satisfies Config;
