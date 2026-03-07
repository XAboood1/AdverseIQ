import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        clinical: {
          // Premium Dark Mode Basis
          navy: "#F8FAFC", // Heading text (white on dark bg)
          "surface-dark": "#0B1120", // Secondary background / cards
          surface: "#0E1525", // Input/card surface
          "surface-alt": "#131B2E", // Alt surface for nested elements
          text: "#F8FAFC", // Pure white for body text
          "text-muted": "#94A3B8", // Slate-400 for muted text
          border: "rgba(255, 255, 255, 0.1)", // subtle borders

          // Muted modern palette
          "slate-800": "#1E293B",
          "slate-700": "#334155",
          "slate-300": "#CBD5E1",

          "muted-blue-start": "#93C5FD", // blue-300
          "muted-blue-end": "#3B82F6", // blue-500

          "muted-teal-start": "#5EEAD4", // teal-300
          "muted-teal-end": "#0D9488", // teal-600

          // Action / Primary - Muted and professional
          blue: "#3B82F6",
          teal: "#0D9488",

          // Status colors
          red: "#ef4444",
          "red-bg": "rgba(239, 68, 68, 0.1)",
          amber: "#f59e0b",
          "amber-bg": "rgba(245, 158, 11, 0.1)",
          green: "#10b981",
          "green-bg": "rgba(16, 185, 129, 0.1)",
        }
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'glow-cyan': 'linear-gradient(to bottom right, var(--tw-gradient-stops))',
        'glow-purple': 'linear-gradient(to bottom right, var(--tw-gradient-stops))',
        'glow-emerald': 'linear-gradient(to bottom right, var(--tw-gradient-stops))',
        'glow-amber': 'linear-gradient(to bottom right, var(--tw-gradient-stops))',
      },
      fontFamily: {
        sans: ["var(--font-inter)", "sans-serif"],
        heading: ["var(--font-plus-jakarta)", "sans-serif"],
      },
      boxShadow: {
        "glow-sm": "0 0 15px -3px rgba(58, 123, 213, 0.15)", // reduced opacity
        "glow-md": "0 0 25px -4px rgba(58, 123, 213, 0.2)", // reduced opacity
        "glass": "0 4px 24px -1px rgba(0, 0, 0, 0.2), 0 0 0 1px rgba(255, 255, 255, 0.05) inset",
      }
    },
  },
  plugins: [],
};
export default config;
