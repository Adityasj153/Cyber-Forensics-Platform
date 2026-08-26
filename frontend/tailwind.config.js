/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0E1420",
        },
        slate: {
          800: "#1A2233",
          600: "#33415A",
        },
        fog: {
          200: "#C9D2E0",
        },
        evidence: {
          amber: "#D98E33",
        },
        trace: {
          cyan: "#4FB8C4",
        },
        critical: "#C9483F",
        verified: "#5FA777",
        disabled: "#5A6478",
        paper: {
          50: "#F7F5F0",
        },
        "ink-900-print": "#1A1A1A",
        "rule-line": "#B8B2A6",
        "print-accent": "#B5651D",
      },
      fontFamily: {
        display: ['"IBM Plex Sans Condensed"', "sans-serif"],
        body: ['"IBM Plex Sans"', "sans-serif"],
        mono: ['"JetBrains Mono"', "monospace"],
      },
      fontSize: {
        "display-lg": ["32px", { lineHeight: "38px", fontWeight: "600" }],
        "display-sm": ["22px", { lineHeight: "28px", fontWeight: "600" }],
        "body-lg": ["16px", { lineHeight: "24px", fontWeight: "400" }],
        "body-sm": ["14px", { lineHeight: "20px", fontWeight: "400" }],
        label: ["12px", { lineHeight: "16px", fontWeight: "500", letterSpacing: "0.04em", textTransform: "uppercase" }],
        "mono-md": ["14px", { lineHeight: "20px", fontWeight: "400" }],
        "mono-sm": ["12px", { lineHeight: "18px", fontWeight: "400" }],
      },
    },
  },
  plugins: [],
};
