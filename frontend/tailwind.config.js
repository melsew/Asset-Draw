/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        // Ethiopic-capable system fallbacks; no external font requests (works offline / low bandwidth).
        sans: ["Inter", "Noto Sans Ethiopic", "Nyala", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
