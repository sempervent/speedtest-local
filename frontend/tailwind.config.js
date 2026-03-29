/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["IBM Plex Sans", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      colors: {
        ink: {
          950: "#070b12",
          900: "#0c1220",
          800: "#121a2b",
          700: "#1b2740",
        },
        accent: {
          DEFAULT: "#5eead4",
          dim: "#2dd4bf",
        },
        warn: "#fbbf24",
      },
    },
  },
  plugins: [],
};
