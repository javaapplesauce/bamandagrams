// .eslintrc.js (at project root or in frontend/)
module.exports = {
  env: {
    browser: true,
    es2021: true,
  },
  extends: [
    "eslint:recommended", 
    "plugin:react/recommended", 
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended",
    "prettier"
  ],
  parser: "@typescript-eslint/parser",
  parserOptions: { ecmaVersion: "latest", sourceType: "module", ecmaFeatures: { jsx: true } },
  plugins: ["react", "@typescript-eslint"],
  settings: { react: { version: "detect" } },
  rules: {
    // custom rules or overrides can be added here
  }
};
