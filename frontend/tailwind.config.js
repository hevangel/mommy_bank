/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        piggy: { DEFAULT: "#F17FB6", soft: "#FDE7F1", deep: "#D95E9C" },
        mint: { DEFAULT: "#63C9A8", soft: "#E2F7EF", deep: "#3EAF8B" },
        sky: { DEFAULT: "#6FB8E8", soft: "#E3F1FB", deep: "#4396CE" },
        butter: { DEFAULT: "#F5C445", soft: "#FCF1D4", deep: "#D9A61F" },
        lav: { DEFAULT: "#A78BFA", soft: "#EFE8FD", deep: "#8263EE" },
        // flat aliases matching class usage like bg-piggysoft
        piggysoft: "#FDE7F1",
        mintsoft: "#E2F7EF",
        skysoft: "#E3F1FB",
        buttersoft: "#FCF1D4",
        lavsoft: "#EFE8FD",
        ink: "#3B3355",
        cream: "#FFF9F2",
      },
      fontFamily: {
        sans: [
          "ui-rounded",
          "SF Pro Rounded",
          "Nunito",
          "Segoe UI",
          "system-ui",
          "-apple-system",
          "sans-serif",
        ],
      },
      boxShadow: {
        soft: "0 4px 16px -4px rgba(59, 51, 85, 0.12)",
        chunky: "0 6px 0 -2px rgba(59, 51, 85, 0.12), 0 12px 24px -8px rgba(59, 51, 85, 0.25)",
        pop: "0 3px 0 0 rgba(0,0,0,0.08)",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-8px)" },
        },
        wiggle: {
          "0%, 100%": { transform: "rotate(-3deg)" },
          "50%": { transform: "rotate(3deg)" },
        },
        pop: {
          "0%": { transform: "scale(0.6)", opacity: "0" },
          "70%": { transform: "scale(1.08)" },
          "100%": { transform: "scale(1)", opacity: "1" },
        },
        drop: {
          "0%": { transform: "translateY(-24px) rotate(-24deg)", opacity: "0" },
          "60%": { transform: "translateY(4px) rotate(6deg)", opacity: "1" },
          "100%": { transform: "translateY(0) rotate(0deg)", opacity: "1" },
        },
        sparkle: {
          "0%, 100%": { opacity: "0.2", transform: "scale(0.8)" },
          "50%": { opacity: "1", transform: "scale(1.15)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        float: "float 4s ease-in-out infinite",
        wiggle: "wiggle 0.5s ease-in-out",
        pop: "pop 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) both",
        drop: "drop 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) both",
        sparkle: "sparkle 2s ease-in-out infinite",
        shimmer: "shimmer 1.6s linear infinite",
      },
    },
  },
  plugins: [],
};
