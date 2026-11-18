# kepler.by — правила для правок сайта

## Не трогать оформление чата
Оформление онлайн-чата лежит в двух файлах: `assets/kplc-mobile.css` и `assets/kplc-mobile.js`.
Они же стоят на сервере kepler.by (`/assets/kplc-mobile.css?v=2`, `/assets/kplc-mobile.js?v=2`)
и используются ещё и на kandix. Если их удалить или перезаписать при пересборке —
дизайн чата собьётся на обоих сайтах.

- Не удалять, не переименовывать, не «чистить» эти файлы и не менять их без прямой просьбы владельца.
- Каждая страница должна подключать оба файла (это делает `tools/mirror.py`; сборка падает, если файла нет
  или страница его не подключает — не обходить эту проверку).
- При выкладке на сервер не удалять `/assets/kplc-mobile.*` — выкладывать поверх, без `rsync --delete`
  и без очистки папки `assets/`.
- Если правите сайт другой сессией Claude — передайте ей это правило.

## Как устроен сайт
- Сайт — статическая копия WordPress 1:1: `src/wpmirror` (выгрузка, `tools/wp_fetch.py`,
  workflow `mirror-wp`) → `tools/mirror.py` → `dist/`.
- Формы Elementor отправляет `assets/kepler-forms.js` (заявка уходит боту через `/?rest_route=/kpl/v1/send`).
- Старые адреса WordPress → `content/site.json` → `redirects`; 301 для nginx — `deploy/nginx-redirects.conf`.
