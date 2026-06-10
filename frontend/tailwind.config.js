/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          orange: '#F97316',
          blue: '#3B82F6',
          purple: '#8B5CF6',
        },
      },
    },
  },
  plugins: [],
}
