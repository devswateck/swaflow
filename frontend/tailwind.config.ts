import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17211f",
        line: "#dfe7e3",
        panel: "#f7faf8",
        brand: "#0f766e",
        warn: "#b45309",
        danger: "#be123c",
      },
      boxShadow: {
        soft: "0 1px 2px rgba(23, 33, 31, 0.08)",
      },
    },
  },
  plugins: [],
} satisfies Config;

