// frontend/tailwind.config.js
module.exports = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      // You can extend theme here (colors, spacing, etc.)
    }
  },
  darkMode: 'class', // toggle dark mode via a top-level 'dark' class on <html> or <body>
  plugins: []
};
