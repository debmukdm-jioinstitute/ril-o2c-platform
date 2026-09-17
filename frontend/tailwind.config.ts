import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Warm, light "consulting-grade" palette — cream surfaces, deep navy ink, gold accent.
        cream: {
          DEFAULT: "#f7f4ee",
          50: "#fdfcfa",
          100: "#f7f4ee",
          200: "#efe9dc",
        },
        ink: {
          DEFAULT: "#16233f",
          700: "#1e2f52",
          600: "#33415f",
          500: "#5b6786",
          400: "#8892a8",
        },
        gold: {
          DEFAULT: "#b8860f",
          50: "#fbf3e0",
          100: "#f3e2b0",
          400: "#c9962c",
          600: "#a4740f",
        },
        line: "#e5e0d3",
      },
      boxShadow: {
        card: "0 1px 2px rgba(22, 35, 63, 0.06), 0 1px 8px rgba(22, 35, 63, 0.04)",
      },
    },
  },
  plugins: [],
};

export default config;
