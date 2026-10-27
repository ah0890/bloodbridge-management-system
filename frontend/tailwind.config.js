/** @type {import('tailwindcss').Config} */
// Colours map to CSS variables defined in src/styles/tokens.css (the single source of design tokens).
const token = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        nav: { DEFAULT: token("nav"), fg: token("nav-fg"), muted: token("nav-muted"), active: token("nav-active") },
        canvas: token("canvas"),
        surface: token("surface"),
        border: token("border"),
        ink: { DEFAULT: token("ink"), muted: token("ink-muted"), subtle: token("ink-subtle") },
        primary: { DEFAULT: token("primary"), fg: token("primary-fg") },
        blood: { DEFAULT: token("blood"), soft: token("blood-soft") },
        success: { DEFAULT: token("success"), soft: token("success-soft") },
        warning: { DEFAULT: token("warning"), soft: token("warning-soft") },
        danger: { DEFAULT: token("danger"), soft: token("danger-soft") },
        info: { DEFAULT: token("info"), soft: token("info-soft") },
        demo: { DEFAULT: token("demo"), soft: token("demo-soft") },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Consolas", "monospace"],
      },
      borderRadius: { sm: "4px", DEFAULT: "6px", md: "8px", lg: "10px" },
      boxShadow: { card: "0 1px 2px 0 rgb(15 23 42 / 0.05)", pop: "0 8px 24px -6px rgb(15 23 42 / 0.18)" },
      fontSize: { "2xs": ["0.6875rem", "1rem"] },
    },
  },
  plugins: [],
};
