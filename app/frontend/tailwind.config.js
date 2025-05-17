/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html', // Если используете Vite, index.html в корне frontend
    './src/**/*.{js,ts,jsx,tsx}', // Сканировать все JS/TS/JSX/TSX файлы в src
  ],
  theme: {
    extend: {}, // Здесь можно расширять стандартную тему Tailwind
  },
  plugins: [],
};
