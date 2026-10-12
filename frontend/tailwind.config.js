// Tailwind build config for index.html (moved from the inline play-CDN config, unchanged).
// Rebuild (needs Node, one-time online install of tailwindcss@3.4.17, @tailwindcss/forms@0.5.9, @tailwindcss/container-queries@0.1.1):
//   npx tailwindcss -c tailwind.config.js -i tailwind.input.css -o static/css/tazks.css --minify
const cfg = {
    darkMode: "class",
    theme: {
      extend: {
        colors: {
          "secondary-fixed": "#e2e2e5", "error-container": "#ffdad6", "secondary-container": "#e2e2e5",
          "on-secondary-fixed-variant": "#454749", "outline-variant": "#bfc9be", "inverse-primary": "#8cd7a0",
          "surface-container-highest": "#d3e4fe", "surface-container-high": "#dce9ff", "on-secondary": "#ffffff",
          "surface-tint": "#206b3e", "tertiary-fixed-dim": "#c5c7c8", "surface-variant": "#d3e4fe",
          "on-primary-fixed-variant": "#00522a", "tertiary": "#5a5c5d", "surface-container-lowest": "#ffffff",
          "on-primary-container": "#f6fff4", "on-secondary-container": "#636467", "tertiary-container": "#737576",
          "on-tertiary-fixed": "#191c1d", "on-tertiary-container": "#fcfdfe", "on-secondary-fixed": "#1a1c1e",
          "on-tertiary": "#ffffff", "secondary": "#5d5e61", "on-error-container": "#93000a",
          "primary-fixed": "#a7f4ba", "primary-container": "#398253", "inverse-surface": "#213145",
          "on-tertiary-fixed-variant": "#454748", "secondary-fixed-dim": "#c6c6c9", "error": "#ba1a1a",
          "primary-fixed-dim": "#8cd7a0", "on-surface": "#0b1c30", "outline": "#707a70",
          "on-background": "#0b1c30", "surface-bright": "#f8f9ff", "on-error": "#ffffff",
          "tertiary-fixed": "#e1e3e4", "surface-container": "#e5eeff", "inverse-on-surface": "#eaf1ff",
          "on-primary": "#ffffff", "surface-dim": "#cbdbf5", "surface-container-low": "#eff4ff",
          "primary": "#1c693c", "on-primary-fixed": "#00210d", "surface": "#f8f9ff",
          "on-surface-variant": "#404941", "background": "#f8f9ff"
        },
        borderRadius: { DEFAULT: "0.25rem", lg: "0.5rem", xl: "0.75rem", full: "9999px" },
        spacing: { "container-max": "1280px", gutter: "24px", "margin-desktop": "40px", "margin-mobile": "16px", unit: "8px" },
        fontFamily: {
          "body-md": ["Hanken Grotesk"], "headline-md": ["Hanken Grotesk"], "headline-lg": ["Hanken Grotesk"],
          "body-sm": ["Hanken Grotesk"], "headline-lg-mobile": ["Hanken Grotesk"], "label-lg": ["Hanken Grotesk"],
          "label-md": ["Hanken Grotesk"], "headline-xl": ["Hanken Grotesk"], "body-lg": ["Hanken Grotesk"]
        },
        fontSize: {
          "body-md": ["16px", { lineHeight: "24px", fontWeight: "400" }],
          "headline-md": ["24px", { lineHeight: "32px", fontWeight: "600" }],
          "headline-lg": ["32px", { lineHeight: "40px", letterSpacing: "-0.01em", fontWeight: "600" }],
          "body-sm": ["14px", { lineHeight: "20px", fontWeight: "400" }],
          "headline-lg-mobile": ["28px", { lineHeight: "36px", fontWeight: "600" }],
          "label-lg": ["14px", { lineHeight: "16px", letterSpacing: "0.05em", fontWeight: "600" }],
          "label-md": ["12px", { lineHeight: "16px", fontWeight: "500" }],
          "headline-xl": ["48px", { lineHeight: "56px", letterSpacing: "-0.02em", fontWeight: "700" }],
          "body-lg": ["18px", { lineHeight: "28px", fontWeight: "400" }]
        }
      }
    }
  };
module.exports = {
  ...cfg,
  content: ["./index.html"],
  plugins: [require("@tailwindcss/forms"), require("@tailwindcss/container-queries")],
};
