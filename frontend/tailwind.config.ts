import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        panel: "#0f172a",
        accent: "#1d9bf0",
      },
    },
  },
  plugins: [],
};

export default config;
