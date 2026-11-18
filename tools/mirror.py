"""Статическая копия WordPress kepler.by 1:1.

Берёт выгрузку tools/wp_fetch.py (src/wpmirror: готовый HTML страниц и все файлы оформления)
и собирает из неё сайт в dist/. Вид страниц — ровно как в WordPress: та же разметка Elementor,
те же CSS, JS, шрифты и картинки. Меняется только «невидимое»:
- убраны служебные ссылки WordPress (wp-json, xmlrpc, ленты, oEmbed, generator);
- убрана капча Cloudflare Turnstile — формы отправляет assets/kepler-forms.js
  (заявка уходит боту, как из онлайн-чата);
- подключено оформление чата assets/kplc-mobile.css и assets/kplc-mobile.js (см. CLAUDE.md);
- старые адреса меток/архивов ведут на живые страницы, sitemap и robots — свои.

Запуск: python3 tools/mirror.py [--base https://тест-адрес] [--out dist]
"""
import json, os, re, shutil, sys, datetime, html as H
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src', 'wpmirror')
DIST = os.path.join(ROOT, 'dist')
S = json.load(open(os.path.join(ROOT, 'content', 'site.json'), encoding='utf-8'))
DOMAIN = S['domain']
BASE = DOMAIN
for k, a in enumerate(sys.argv):
    if a == '--base' and k + 1 < len(sys.argv):
        BASE = sys.argv[k + 1].rstrip('/')
    if a == '--out' and k + 1 < len(sys.argv):
        DIST = sys.argv[k + 1]
TEST = BASE != DOMAIN

# Обязательные файлы оформления чата. Без них сборка падает — см. CLAUDE.md.
REQUIRED = ['assets/kplc-mobile.css', 'assets/kplc-mobile.js', 'assets/kepler-forms.js']
CHAT_TAGS = ('<link rel="stylesheet" href="{b}/assets/kplc-mobile.css?v=2">'
             '<script src="{b}/assets/kplc-mobile.js?v=2" defer></script>')

DROP_HEAD = [
    r"<link rel='dns-prefetch' href='//challenges\.cloudflare\.com' />\s*",
    r'<link rel="alternate" type="application/rss\+xml"[^>]*>\s*',
    r'<link rel="alternate" title="oEmbed[^>]*>\s*',
    r'<link rel="https://api\.w\.org/"[^>]*>\s*',
    r'<link rel="alternate" title="JSON" type="application/json"[^>]*>\s*',
    r'<link rel="EditURI"[^>]*>\s*',
    r'<meta name="generator"[^>]*>\s*',
    r"<link rel='shortlink'[^>]*>\s*",
]
DROP_SCRIPTS = ['cfturnstile-js-before', 'cfturnstile-js', 'cfturnstile-elementor-forms-js-extra',
                'cfturnstile-elementor-forms-js']


def rel_host(s):
    """Тестовая копия: адреса kepler.by → тестовый адрес (кроме API бота)."""
    if not TEST:
        return s
    s = re.sub(r'https://kepler\.by(?=/(?!\?rest_route))', BASE, s)
    s = re.sub(r'https:\\/\\/kepler\.by(?=\\/)', BASE.replace('/', '\\/'), s)
    s = re.sub(r'(["\'(])/(wp-content|wp-includes|assets)/', lambda m: m.group(1) + urlpath(BASE) + '/' + m.group(2) + '/', s)
    return s


def urlpath(b):
    m = re.match(r'https?://[^/]+(/.*)?', b)
    return (m.group(1) or '') if m else ''


def process(h):
    for p in DROP_HEAD:
        h = re.sub(p, '', h)
    for sid in DROP_SCRIPTS:
        h = re.sub(r'<script[^>]*id="' + re.escape(sid) + r'"[^>]*>.*?</script>\s*', '', h, flags=re.S)
    h = re.sub(r'<div[^>]*class="[^"]*cf-turnstile[^"]*"[^>]*>\s*</div>', '', h)
    if TEST:
        h = re.sub(r"<meta name='robots' content='[^']*' />", '', h)
        h = h.replace('<meta charset="UTF-8">', '<meta charset="UTF-8"><meta name="robots" content="noindex, nofollow">', 1)
    b = urlpath(BASE) if TEST else ''
    tail = CHAT_TAGS.format(b=b) + f'<script src="{b}/assets/kepler-forms.js" defer></script>'
    assert h.count('</body>') == 1, 'нет </body>'
    h = h.replace('</body>', tail + '\n</body>')
    return rel_host(h)


def write(path, content):
    fp = os.path.join(DIST, path.strip('/'), 'index.html') if not path.endswith('.html') else os.path.join(DIST, path.strip('/'))
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)


def redirects():
    for old, new in S.get('redirects', {}).items():
        fp = os.path.join(DIST, old.strip('/')) if old.endswith('.html') else os.path.join(DIST, old.strip('/'), 'index.html')
        if os.path.exists(fp):
            continue
        to = BASE + quote(new)
        write(old, f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Страница перенесена</title>
<link rel="canonical" href="{DOMAIN + quote(new)}"><meta name="robots" content="noindex, follow">
<meta http-equiv="refresh" content="0; url={to}"><script>location.replace({json.dumps(to)})</script></head>
<body><p>Страница перенесена: <a href="{to}">{H.escape(DOMAIN + new)}</a></p></body></html>''')


def main():
    for r in REQUIRED:
        if not os.path.exists(os.path.join(ROOT, r)) or os.path.getsize(os.path.join(ROOT, r)) == 0:
            sys.exit(f'ОШИБКА: нет {r}. Это оформление чата kepler.by/kandix — восстановите файл (см. CLAUDE.md).')
    if os.path.exists(DIST):
        shutil.rmtree(DIST)
    files = os.path.join(SRC, 'files')
    shutil.copytree(files, DIST)
    if TEST:  # абсолютные адреса kepler.by внутри CSS/JS
        for d, _, fs in os.walk(DIST):
            for fn in fs:
                if fn.endswith(('.css', '.js')):
                    fp = os.path.join(d, fn)
                    s = open(fp, encoding='utf-8', errors='surrogateescape').read()
                    s2 = rel_host(s)
                    if s2 != s:
                        open(fp, 'w', encoding='utf-8', errors='surrogateescape').write(s2)
    os.makedirs(os.path.join(DIST, 'assets'), exist_ok=True)
    for fn in os.listdir(os.path.join(ROOT, 'assets')):
        if fn.startswith(('kplc-mobile', 'kepler-forms')) or fn == 'logo.png':
            shutil.copy(os.path.join(ROOT, 'assets', fn), os.path.join(DIST, 'assets', fn))
    pages = json.load(open(os.path.join(SRC, 'pages.json'), encoding='utf-8'))
    sm = []
    for p in pages:
        h = open(os.path.join(SRC, 'html', p['path'].strip('/'), 'index.html'), encoding='utf-8').read()
        out = process(h)
        write(p['path'], out)
        if not re.search(r"<meta name='robots' content='noindex", h):
            sm.append((p['path'], (p.get('modified') or '')[:10] or datetime.date.today().isoformat()))
    p404 = os.path.join(SRC, 'html', '404.html')
    if os.path.exists(p404):
        with open(os.path.join(DIST, '404.html'), 'w', encoding='utf-8') as f:
            f.write(process(open(p404, encoding='utf-8', errors='ignore').read()))
    redirects()
    cat = '/category/vse-stati/'
    if cat not in [x[0] for x in sm]:
        sm.append((cat, datetime.date.today().isoformat()))
    xml = ''.join(f'<url><loc>{DOMAIN}{quote(u)}</loc><lastmod>{d}</lastmod></url>' for u, d in sorted(sm))
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{xml}</urlset>'
    for fn in ('sitemap.xml', 'sitemap_index.xml', 'page-sitemap.xml', 'post-sitemap.xml'):
        open(os.path.join(DIST, fn), 'w', encoding='utf-8').write(xml)
    open(os.path.join(DIST, 'robots.txt'), 'w').write(
        'User-agent: *\nDisallow: /\n' if TEST else f'User-agent: *\nAllow: /\n\nSitemap: {DOMAIN}/sitemap.xml\n')
    st = os.path.join(ROOT, 'static')
    if os.path.isdir(st):
        for fn in os.listdir(st):
            shutil.copy(os.path.join(st, fn), os.path.join(DIST, fn))
    open(os.path.join(DIST, '.nojekyll'), 'w').write('')
    # проверка: на каждой странице есть оформление чата и обработчик форм
    bad = []
    for d, _, fs in os.walk(DIST):
        for fn in fs:
            if fn.endswith('.html'):
                s = open(os.path.join(d, fn), encoding='utf-8').read()
                if 'http-equiv="refresh"' in s or os.path.exists(os.path.join(ROOT, 'static', fn)):
                    continue
                if 'kplc-mobile.css' not in s or 'kplc-mobile.js' not in s or 'kepler-forms.js' not in s:
                    bad.append(os.path.relpath(os.path.join(d, fn), DIST))
    if bad:
        sys.exit('ОШИБКА: без оформления чата: ' + ', '.join(bad[:10]))
    print('страниц:', len(pages), 'в sitemap:', len(sm), '→', DIST)


if __name__ == '__main__':
    main()
