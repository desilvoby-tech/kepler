"""Выгрузка живого WordPress kepler.by «как есть» — для статической копии 1:1.

Запускается в GitHub Actions (workflow mirror-wp). Что делает:
1. Берёт список страниц и записей из REST API WordPress.
2. Получает готовый HTML каждой страницы. GET по адресу страницы теперь отдаёт статику,
   поэтому страница запрашивается у WordPress напрямую: POST /index.php?page_id=ID
   (на POST WordPress не делает редирект на «красивый» адрес и отдаёт страницу целиком).
3. Открывает каждую страницу в Chromium (компьютер и телефон), прокручивает до конца
   и записывает все файлы, которые браузер скачал с kepler.by: CSS, JS, шрифты, картинки,
   в том числе подгружаемые позже (куски Elementor, фоны, ленивые картинки).
4. Докачивает всё, что упомянуто в HTML и CSS, но браузер не запросил.
5. Делает скриншоты оригинала — по ним потом сверяется копия.
Результат: src/wpmirror/html/…, src/wpmirror/files/… (те же пути, что на сайте), src/wpmirror/shots/…
"""
import asyncio, json, os, re, sys, time, urllib.request, urllib.error
from urllib.parse import urlparse, unquote, urljoin, quote

H = 'https://kepler.by'
OUT = 'src/wpmirror'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36'
ASSET = re.compile(r'^/(wp-content|wp-includes)/')


def req(url, method='GET', tries=4):
    for t in range(tries):
        try:
            r = urllib.request.Request(url, method=method, data=b'' if method == 'POST' else None,
                                       headers={'User-Agent': UA, 'Referer': H + '/'})
            with urllib.request.urlopen(r, timeout=60) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                return e.code, e.read()
            time.sleep(2 + t * 3)
        except Exception:
            time.sleep(2 + t * 3)
    return 0, b''


def rest(kind):
    items, page = [], 1
    while True:
        st, b = req(f'{H}/index.php?rest_route=/wp/v2/{kind}&per_page=100&page={page}&_fields=id,link,modified,status')
        if st != 200:
            break
        lst = json.loads(b)
        if not lst:
            break
        items += lst
        if len(lst) < 100:
            break
        page += 1
    return items


def save(rel, data):
    fp = os.path.join(OUT, rel.lstrip('/'))
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, 'wb') as f:
        f.write(data)


def targets():
    t = []
    for p in rest('pages'):
        t.append((unquote(urlparse(p['link']).path), f'{H}/index.php?page_id={p["id"]}', p['modified']))
    for p in rest('posts'):
        t.append((unquote(urlparse(p['link']).path), f'{H}/index.php?p={p["id"]}', p['modified']))
    t.append(('/category/vse-stati/', f'{H}/index.php?category_name=vse-stati', ''))
    return t


FILES = {}   # путь на сайте -> True (скачан)


def want(url):
    u = urlparse(url)
    if u.netloc not in ('kepler.by', 'www.kepler.by', ''):
        return None
    p = unquote(u.path)
    return p if ASSET.match(p) else None


def grab(path):
    if path in FILES:
        return
    FILES[path] = False
    st, b = req(H + quote(path, safe='/%:@&=+$,;~!*\'()'))
    if st == 200 and b and not b.lstrip()[:15].lower().startswith((b'<!doctype', b'<html')):
        save('files' + path, b)
        FILES[path] = True
        if path.endswith('.css'):
            css_deps(path, b.decode('utf-8', 'ignore'))
    else:
        print('нет файла', st, path)


def css_deps(path, css):
    for m in re.findall(r'url\(\s*["\']?([^"\')]+)', css):
        if m.startswith('data:'):
            continue
        p = want(urljoin(H + path, m.strip()))
        if p:
            grab(p)
    for m in re.findall(r'@import\s+["\']([^"\']+)', css):
        p = want(urljoin(H + path, m))
        if p:
            grab(p)


def html_deps(html):
    html = html.replace('\\/', '/')
    for m in re.findall(r'(?:https?:)?//kepler\.by(/wp-(?:content|includes)/[^"\'\s<>)\\,]+)', html):
        grab(unquote(m.split('?')[0].split('#')[0]))
    for m in re.findall(r'(?:src|href|data-src|data-bg|poster)=["\'](/wp-(?:content|includes)/[^"\']+)', html):
        grab(unquote(m.split('?')[0]))
    for m in re.findall(r'url\(\s*["\']?((?:https?://kepler\.by)?/wp-[^"\')]+)', html):
        p = want(urljoin(H + '/', m))
        if p:
            grab(p)


async def browse(tlist):
    from playwright.async_api import async_playwright
    seen = set()
    async with async_playwright() as pw:
        br = await pw.chromium.launch()
        for vp, name in [({'width': 1366, 'height': 900}, 'desktop'), ({'width': 390, 'height': 844}, 'mobile')]:
            ctx = await br.new_context(viewport=vp, user_agent=UA if name == 'desktop' else None,
                                       is_mobile=(name == 'mobile'), has_touch=(name == 'mobile'), device_scale_factor=1)
            for path, _, _ in tlist:
                html = open(os.path.join(OUT, 'html', path.strip('/'), 'index.html'), encoding='utf-8').read()
                page = await ctx.new_page()
                doc_url = H + quote(path)

                async def handle(route, html=html, doc_url=doc_url):
                    if route.request.resource_type == 'document' and route.request.url.split('#')[0] in (doc_url, doc_url.lower()):
                        await route.fulfill(status=200, content_type='text/html; charset=utf-8', body=html)
                    else:
                        await route.continue_()
                await page.route('**/*', handle)
                page.on('request', lambda r: seen.add(r.url))
                try:
                    await page.goto(doc_url, wait_until='networkidle', timeout=90000)
                except Exception as e:
                    print('goto', path, e)
                h = await page.evaluate('document.body.scrollHeight')
                y = 0
                while y < h:
                    y += 500
                    await page.evaluate(f'window.scrollTo(0,{y})')
                    await page.wait_for_timeout(120)
                    h = await page.evaluate('document.body.scrollHeight')
                await page.wait_for_timeout(1500)
                await page.evaluate('window.scrollTo(0,0)')
                await page.wait_for_timeout(800)
                slug = path.strip('/').replace('/', '__') or 'index'
                os.makedirs(os.path.join(OUT, 'shots', name), exist_ok=True)
                await page.screenshot(path=os.path.join(OUT, 'shots', name, slug + '.png'), full_page=True)
                await page.close()
            await ctx.close()
        await br.close()
    return seen


def main():
    tl = targets()
    print('страниц:', len(tl))
    meta = []
    for path, src, mod in tl:
        st, b = req(src, 'POST')
        ok = st == 200 and b'</html>' in b
        print(st, len(b), path)
        if ok:
            save(os.path.join('html', path.strip('/'), 'index.html'), b)
            meta.append({'path': path, 'src': src, 'modified': mod})
    st, b = req(H + '/net-takoj-stranicy-kepler/')
    save('html/404.html', b)
    for f in ('sitemap_index.xml', 'page-sitemap.xml', 'post-sitemap.xml', 'category-sitemap.xml'):
        st, b = req(f'{H}/index.php?sitemap={f.split("-")[0].replace(".xml", "")}' if False else f'{H}/{f}')
    json.dump(meta, open(os.path.join(OUT, 'pages.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for m in meta:
        html_deps(open(os.path.join(OUT, 'html', m['path'].strip('/'), 'index.html'), encoding='utf-8').read())
    html_deps(open(os.path.join(OUT, 'html/404.html'), encoding='utf-8', errors='ignore').read())
    print('файлов из HTML/CSS:', sum(FILES.values()))
    tl_ok = [(m['path'], m['src'], m['modified']) for m in meta]
    seen = asyncio.run(browse(tl_ok))
    ext = set()
    for u in seen:
        p = want(u)
        if p:
            grab(p)
        elif urlparse(u).netloc not in ('kepler.by', ''):
            ext.add(urlparse(u).netloc)
    print('всего файлов:', sum(FILES.values()), 'не скачано:', [k for k, v in FILES.items() if not v][:50])
    json.dump({'files': sorted(k for k, v in FILES.items() if v), 'external_hosts': sorted(ext)},
              open(os.path.join(OUT, 'files.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
