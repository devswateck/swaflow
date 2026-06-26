import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#f6f7fb",
        surface: "#ffffff",
        surfaceMuted: "#eef0f6",
        ink: "#14111f",
        inkMuted: "#6d6a7a",
        inkSubtle: "#9691a6",
        line: "#dadde8",
        brand: "#7c3aed",
        brandNight: "#0b0614",
        brandDeep: "#160a24",
        brandPanel: "#211833",
        brandAccent: "#ff3de8",
        brandAccentSoft: "#f1d9ff",
        brandOnDark: "#f8f2ff",
        success: "#0891b2",
        warn: "#f59e0b",
        danger: "#e11d48",
      },
      boxShadow: {
        soft: "0 1px 2px rgba(11, 6, 20, 0.14)",
        glow: "0 0 0 1px rgba(255, 61, 232, 0.16), 0 18px 45px rgba(11, 6, 20, 0.24)",
      },
    },
  },
  plugins: [],
} satisfies Config;
