# kepler.by — статическая копия WordPress 1:1

Сайт сервисного центра «Кеплер» (Гомель). Вид, тексты, формы и SEO — ровно как в WordPress:
страницы выгружены из живого WordPress вместе со всеми CSS, JS, шрифтами и картинками.

**Важно:** оформление онлайн-чата — `assets/kplc-mobile.css` и `assets/kplc-mobile.js`. Не удалять и не менять,
при выкладке не затирать на сервере. Подробно — в `CLAUDE.md`.

## Как устроено
- `src/wpmirror/html/` — HTML страниц из WordPress, `src/wpmirror/files/` — файлы `/wp-content`, `/wp-includes`.
- `tools/wp_fetch.py` (workflow **mirror-wp**) — заново выгрузить WordPress, если там что-то поменяли.
- `tools/mirror.py` — собирает сайт в `dist/`: убирает служебные ссылки WordPress и капчу Cloudflare,
  подключает `assets/kepler-forms.js` (формы → бот → Telegram) и оформление чата, делает sitemap, robots
  и переходы со старых адресов.
- `tools/compare.py` (workflow **compare**) — сверяет копию с оригиналом на компьютере и телефоне,
  отчёт в `src/wpmirror/compare/`.
- `deploy/nginx-redirects.conf` — 301-редиректы для nginx.

## Сборка
    python3 tools/mirror.py                 # для kepler.by → dist/
    python3 tools/mirror.py --base https://desilvoby-tech.github.io/kepler   # тестовая копия

Выкладка на сервер: содержимое `dist/` поверх папки сайта, **без удаления** файлов, которых нет в `dist/`
(в первую очередь `assets/kplc-mobile.*`).

Старая сборка из `content/*.json` (`tools/build.py`) оставлена для истории и больше не используется.
