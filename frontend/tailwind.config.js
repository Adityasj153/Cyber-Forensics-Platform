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
      },
      fontFamily: {
        display: ['"IBM Plex Sans Condensed"', "sans-serif"],
        body: ['"IBM Plex Sans"', "sans-serif"],
        mono: ['"JetBrains Mono"', "monospace"],
      },
    },
  },
  plugins: [],
};
