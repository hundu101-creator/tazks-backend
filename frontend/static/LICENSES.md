# Vendored assets (offline use) - TAZKS fix 4, 2026-10-13

| File | Source | Version / date | Licence |
|---|---|---|---|
| vendor/telegram-web-app.js | https://telegram.org/js/telegram-web-app.js | downloaded 2026-10-13 | Telegram's official Mini App SDK, published by Telegram for Mini Apps to load; no separate licence file is shipped with it (Telegram terms apply). Inside Telegram the client provides the WebApp bridge; this local copy only replaces the network fetch. |
| css/tazks.css, css/admin.css | Built with Tailwind CSS 3.4.17 + @tailwindcss/forms 0.5.9 + @tailwindcss/container-queries 0.1.1 from ../tailwind*.config.js | built 2026-10-13 | MIT (Tailwind Labs) |
| fonts/hanken-grotesk-*.woff2 | Google Fonts, Hanken Grotesk 400-700 (v12) | downloaded 2026-10-13 | SIL Open Font License 1.1 |
| fonts/material-symbols-outlined-*.woff2 | Google Fonts, Material Symbols Outlined (wght 100-700, FILL 0-1) | downloaded 2026-10-13 | Apache License 2.0 |
| css/fonts.css | Google Fonts CSS with URLs rewritten to ../fonts/ | 2026-10-13 | same as the fonts |

Still online by nature (content, not app shell): YouTube embeds/thumbnails for tutorial videos, admin-entered image URLs, the t.me referral link, and the deployed Render API when the page is opened outside localhost.
