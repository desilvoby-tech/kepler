# kepler.by — статическая версия

Сайт сервисного центра «Кеплер» (Гомель). Контент — в `content/`, сборка — `tools/build.py`,
публикация — GitHub Actions → GitHub Pages (`.github/workflows/deploy.yml`).

- `content/site.json` — телефон, адрес, меню, бренды, общие настройки.
- `content/pages/*.json` — по файлу на страницу: блоки hero, problems, services, table, tabs, steps, faq, seo_text…
- `wp-content/uploads/` — картинки, перенесённые со старого WordPress (те же пути).

Локально: `python3 tools/build.py` → папка `dist/`.
