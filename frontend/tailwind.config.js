/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#eff6ff",
          100: "#dbeafe",
          200: "#bfdbfe",
          300: "#93c5fd",
          400: "#60a5fa",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          800: "#1e40af",
          900: "#1e3a8a",
        },
        surface: {
          DEFAULT: "#0f172a",
          card:    "#1e293b",
          hover:   "#334155",
          border:  "#334155",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains)", "monospace"],
      },
      animation: {
        "fade-in":     "fadeIn 0.4s ease-out",
        "slide-up":    "slideUp 0.4s ease-out",
        "pulse-slow":  "pulse 3s ease-in-out infinite",
        "spin-slow":   "spin 8s linear infinite",
        "shimmer":     "shimmer 2s linear infinite",
      },
      keyframes: {
        fadeIn:  { "0%": { opacity: 0 }, "100%": { opacity: 1 } },
        slideUp: { "0%": { opacity: 0, transform: "translateY(16px)" }, "100%": { opacity: 1, transform: "translateY(0)" } },
        shimmer: {
          "0%":   { backgroundPosition: "200% 0" },
          "100%": { backgroundPosition: "-200% 0" },
        },
      },
      backgroundImage: {
        "grid-slate":      "url(\"data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32' width='32' height='32' fill='none' stroke='rgb(148 163 184 / 0.04)'%3e%3cpath d='M0 .5H31.5V32'/%3e%3c/svg%3e\")",
        "hero-gradient":   "radial-gradient(ellipse 80% 60% at 50% -10%, #1e40af33, transparent)",
        "card-shine":      "linear-gradient(135deg, rgba(255,255,255,0.04) 0%, transparent 60%)",
      },
      boxShadow: {
        "glow":      "0 0 20px rgba(59,130,246,0.2)",
        "glow-lg":   "0 0 40px rgba(59,130,246,0.25)",
        "card":      "0 4px 24px rgba(0,0,0,0.35)",
        "card-hover":"0 8px 40px rgba(0,0,0,0.5)",
        "inner-glow":"inset 0 1px 0 rgba(255,255,255,0.05)",
      },
      borderRadius: {
        DEFAULT: "0.5rem",
        lg: "0.75rem",
        xl: "1rem",
        "2xl": "1.25rem",
      },
    },
  },
  plugins: [],
};
