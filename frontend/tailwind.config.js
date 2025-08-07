/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "../templates/**/*.html",   // Django templates
    "./index.js",               // your JS entry that uses htmx/alpine classes
  ],
  theme: { extend: {} },
  plugins: [],
};
