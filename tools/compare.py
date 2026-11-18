"""Сверка копии с оригиналом WordPress (запускается в GitHub Actions, workflow compare).

Оригинал: HTML из src/wpmirror/html подставляется браузеру по адресу kepler.by, всё остальное
грузится с живого WordPress. Копия: dist, собранный mirror.py с --base http://localhost:8765.
Обе версии рендерятся в одном и том же Chromium, на компьютере и телефоне.
Отчёт: src/wpmirror/compare/report.json + картинки «оригинал | копия» для страниц с расхождениями.
"""
import asyncio, json, os, sys
from urllib.parse import quote
from playwright.async_api import async_playwright
from PIL import Image, ImageChops

SRC = 'src/wpmirror'
OUT = os.path.join(SRC, 'compare')
H = 'https://kepler.by'
LOCAL = 'http://localhost:8765'
VIEWS = [('desktop', {'width': 1366, 'height': 900}, False), ('mobile', {'width': 390, 'height': 844}, True)]


async def shoot(ctx, url, out, html=None):
    page = await ctx.new_page()
    bad, errs = [], []
    if html is not None:
        async def handle(route, request):
            if request.resource_type == 'document' and request.url.split('#')[0].lower() == url.lower():
                await route.fulfill(status=200, content_type='text/html; charset=utf-8', body=html)
            else:
                await route.continue_()
        await page.route('**/*', handle)
    page.on('response', lambda r: bad.append(f'{r.status} {r.url}') if r.status >= 400 and ('localhost' in r.url or 'kepler.by' in r.url) else None)
    page.on('pageerror', lambda e: errs.append(str(e)[:200]))
    try:
        await page.goto(url, wait_until='networkidle', timeout=90000)
    except Exception as e:
        errs.append('goto ' + str(e)[:120])
    h = await page.evaluate('document.body.scrollHeight')
    y = 0
    while y < h:
        y += 500
        await page.evaluate(f'window.scrollTo(0,{y})')
        await page.wait_for_timeout(100)
        h = await page.evaluate('document.body.scrollHeight')
    await page.wait_for_timeout(2500)
    await page.evaluate('window.scrollTo(0,0)')
    await page.wait_for_timeout(1000)
    # капча Cloudflare в оригинале — убрана в копии; убираем её и тут, чтобы сравнивать остальное
    await page.evaluate("document.querySelectorAll('.cf-turnstile,[class*=turnstile]').forEach(e=>e.remove())")
    await page.wait_for_timeout(300)
    await page.screenshot(path=out, full_page=True)
    await page.close()
    return bad, errs


def diff(a_path, b_path):
    a, b = Image.open(a_path).convert('L'), Image.open(b_path).convert('L')
    h = min(a.height, b.height)
    d = ImageChops.difference(a.crop((0, 0, a.width, h)), b.crop((0, 0, a.width, h)))
    px = sum(1 for v in d.getdata() if v > 40)
    return a.height, b.height, round(px / (a.width * h) * 100, 3)


def side(a_path, b_path, out):
    a, b = Image.open(a_path).convert('RGB'), Image.open(b_path).convert('RGB')
    h = max(a.height, b.height)
    im = Image.new('RGB', (a.width * 2 + 16, h), (230, 0, 0))
    im.paste(a, (0, 0)); im.paste(b, (a.width + 16, 0))
    im.thumbnail((1600, 12000))
    im.save(out, quality=70)


async def main():
    pages = json.load(open(os.path.join(SRC, 'pages.json'), encoding='utf-8'))
    os.makedirs(OUT, exist_ok=True)
    tmp = '/tmp/cmp'
    os.makedirs(tmp, exist_ok=True)
    report = []
    async with async_playwright() as pw:
        br = await pw.chromium.launch()
        for name, vp, mob in VIEWS:
            ctx = await br.new_context(viewport=vp, is_mobile=mob, has_touch=mob, device_scale_factor=1)
            for p in pages:
                path = p['path']
                slug = path.strip('/').replace('/', '__') or 'index'
                html = open(os.path.join(SRC, 'html', path.strip('/'), 'index.html'), encoding='utf-8').read()
                a, b = f'{tmp}/{name}-{slug}-orig.png', f'{tmp}/{name}-{slug}-copy.png'
                bad_o, err_o = await shoot(ctx, H + quote(path), a, html)
                bad_c, err_c = await shoot(ctx, LOCAL + quote(path), b)
                ha, hb, pct = diff(a, b)
                r = {'view': name, 'path': path, 'h_orig': ha, 'h_copy': hb, 'diff_pct': pct,
                     'copy_404': [x for x in bad_c if not any(x.split(' ', 1)[1].replace(LOCAL, '') in y for y in bad_o)],
                     'copy_js_errors': [e for e in err_c if e not in err_o]}
                if pct > 0.5 or abs(ha - hb) > 4:
                    side(a, b, os.path.join(OUT, f'{name}-{slug}.jpg'))
                report.append(r)
                print(json.dumps(r, ensure_ascii=False), flush=True)
            await ctx.close()
        await br.close()
    json.dump(report, open(os.path.join(OUT, 'report.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    asyncio.run(main())
