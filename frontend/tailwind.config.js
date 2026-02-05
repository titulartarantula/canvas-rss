/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Canvas-inspired color palette
        canvas: {
          primary: '#0374B5',
          secondary: '#394B58',
          success: '#0B874B',
          warning: '#BF4D00',
          danger: '#D64242',
          light: '#F5F5F5',
        }
      }
    },
  },
  plugins: [],
}
