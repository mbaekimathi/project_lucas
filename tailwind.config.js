/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './static/js/**/*.js',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'brand-primary': 'var(--brand-primary, #800020)',
        'brand-secondary': 'var(--brand-secondary, #A00030)',
        'brand-maroon': 'var(--brand-primary, #800020)',
        'brand-maroon-dark': 'var(--brand-accent, #5C0014)',
        'brand-maroon-light': 'var(--brand-secondary, #A00030)',
      },
      fontFamily: {
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
        heading: ['var(--font-sans)', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
