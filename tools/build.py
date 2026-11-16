"""Собирает статический сайт kepler.by из content/ в dist/.

Запуск: python3 tools/build.py [--base https://тест-адрес]
Контент правится в content/pages/*.json и content/site.json, шаблоны — здесь.
"""
import json, glob, os, re, shutil, html, sys, datetime
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = os.path.join(ROOT, 'content')
DIST = os.path.join(ROOT, 'dist')
S = json.load(open(os.path.join(C, 'site.json'), encoding='utf-8'))
BASE = S['domain']
PREFIX = ''   # для превью с диска: file:///…/kepler-preview, для GitHub Pages: /kepler
INDEX = False  # дописывать index.html к ссылкам (только превью с диска)
for k, a in enumerate(sys.argv):
    if a == '--base' and k + 1 < len(sys.argv):
        BASE = sys.argv[k + 1].rstrip('/')
    if a == '--preview' and k + 1 < len(sys.argv):
        PREFIX = sys.argv[k + 1].rstrip('/'); INDEX = True
    if a == '--prefix' and k + 1 < len(sys.argv):
        PREFIX = sys.argv[k + 1].rstrip('/')
    if a == '--out' and k + 1 < len(sys.argv):
        DIST = sys.argv[k + 1]
TODAY = datetime.date.today().isoformat()

esc = lambda s: html.escape(s or '', quote=True)


def load_pages():
    pages = {}
    for f in glob.glob(os.path.join(C, 'pages', '*.json')):
        p = json.load(open(f, encoding='utf-8'))
        p['_file'] = os.path.basename(f)
        pages[p['path']] = p
    return pages


PAGES = load_pages()


def no_bang(s):
    return re.sub(r'\s*!+\s*$', '', s or '').strip()


def h1_of(p):
    for b in p['blocks']:
        if b['type'] == 'hero':
            return no_bang(b['h1'])
    return no_bang(p['title'])


def url(path):
    """Ссылка внутри сайта: кириллица кодируется, как у WordPress."""
    if PREFIX and path.startswith('/'):
        return PREFIX + quote(path, safe='/#?=&:') + ('index.html' if INDEX and path.endswith('/') else '')
    return quote(path, safe='/#?=&:')


def abs_url(path):
    return BASE + quote(path, safe='/#?=&:')


# ---------- блоки ----------
def phone_link(cls='btn'):
    return f'<a class="{cls}" href="tel:{S["phone"]}" data-goal="click_phone">{esc(S["phone_display"])}</a>'


def b_hero(b, p):
    bullets = ''.join(f'<li>{esc(x)}</li>' for x in b.get('bullets', []))
    stats = ''.join(
        f'<div class="stat"><i class="ico ico-{"price" if i == 0 else "time"}"></i><div><span>{esc(s["label"])}</span><b>{esc(s["value"].rstrip("."))}</b></div></div>'
        for i, s in enumerate(b.get('stats', [])))
    lead = f'<div class="lead">{b["lead"]}</div>' if b.get('lead') else ''
    img = b.get('image') or ''
    pic = f'<div class="hero-pic"><img src="{esc(img)}" alt="{esc(no_bang(b["h1"]))}" fetchpriority="high"></div>' if img else ''
    return f'''<section class="hero-wrap"><div class="wrap"><div class="hero{' has-pic' if img else ''}">
<div class="hero-txt"><h1>{esc(no_bang(b["h1"]))}</h1>{lead}
{f'<ul class="hero-list">{bullets}</ul>' if bullets else ''}
<div class="hero-row">{stats}<div class="hero-cta"><a class="hero-phone" href="tel:{S["phone"]}" data-goal="click_phone">{esc(S["phone_display"])}</a><button class="btn btn-white" data-open-form>Заказать ремонт</button></div></div></div>
{pic}</div></div></section>'''


def b_problems(b, p):
    cards = ''
    for c in b['items']:
        img = f'<img src="{esc(c["image"])}" alt="" loading="lazy" width="44" height="44">' if c.get('image') else ''
        cards += f'''<div class="prob"><div class="prob-head"><h3>{esc(c["title"])}</h3>{img}</div>
<div class="prob-body"><span class="lbl">Признак поломки</span><p>{esc(c["symptom"])}</p>
<div class="prob-foot"><div><span class="lbl">Цена ремонта</span><b>{esc(c["price"])}</b></div>
<button class="btn btn-sm" data-open-form data-service="{esc(c["title"])}">Заказать ремонт</button></div></div></div>'''
    title = b.get('title') or 'Частые поломки'
    return f'<section class="sec dark"><div class="wrap"><h2>{esc(title)}</h2><div class="grid3">{cards}</div></div></section>'


def b_services(b, p):
    cards = ''
    links = {x['title'].lower(): x['url'] for g in S['nav'] for x in g.get('children', [])}
    for k, c in enumerate(b['items']):
        t = c['title']
        href = next((u for kk, u in links.items() if t.lower().rstrip('ы').rstrip('и')[:6] in kk), '')
        pts = ''.join(f'<li>{esc(x)}</li>' for x in c.get('points', []))
        photo = c.get('photo') or ''
        icon = f'<img class="svc-ico" src="{esc(c["image"])}" alt="" loading="lazy" width="48" height="48">' if c.get('image') and not photo else ''
        ph = f'<img class="svc-photo" src="{esc(photo)}" alt="{esc(t)}" loading="lazy">' if photo else ''
        desc = f'<p>{esc(c["desc"])}</p>' if c.get('desc') else ''
        head = f'<a href="{url(href)}">{esc(t)}</a>' if href else esc(t)
        wide = ' wide' if photo and c.get('wide') else ''
        cards += f'''<div class="svc{wide}{' has-photo' if photo else ''}">{icon}<div class="svc-txt"><h3>{head}<span>{esc(c["price"].replace("от ", "ОТ ").replace("от", "ОТ"))}</span></h3>{desc}{f'<ul>{pts}</ul>' if pts else ''}
<a class="svc-call" href="tel:{S["phone"]}" aria-label="Позвонить" data-goal="click_phone"></a></div>{ph}</div>'''
    title = f'<h2>{esc(b["title"])}</h2>' if b.get('title') else ''
    return f'<section class="sec"><div class="wrap">{title}<div class="svc-grid">{cards}</div></div></section>'


def table_html(head, rows):
    th = ''.join(f'<th>{esc(h)}</th>' for h in head) if head else ''
    trs = ''
    for r in rows:
        trs += '<tr>' + ''.join(f'<td>{esc(c)}</td>' for c in r) + '</tr>'
    return f'<div class="tbl"><table>{f"<thead><tr>{th}</tr></thead>" if th else ""}<tbody>{trs}</tbody></table></div>'


def b_table(b, p):
    title = f'<h2>{esc(b["title"])}</h2>' if b.get('title') else ''
    return f'<section class="sec dark"><div class="wrap">{title}<div class="panel">{table_html(b.get("head"), b["rows"])}<p class="note">Точную стоимость назовём после бесплатной диагностики, до начала работ.</p></div></div></section>'


def b_tabs(b, p):
    nav = ''.join(f'<button role="tab" aria-selected="{"true" if i == 0 else "false"}" data-tab="{i}">{esc(t["title"])}</button>'
                  for i, t in enumerate(b['items']))
    panes = ''
    for i, t in enumerate(b['items']):
        rows = t['rows']
        head = rows[0] if rows and re.search('Поломка|Услуга', rows[0][0]) else []
        body = rows[1:] if head else rows
        panes += f'<div class="pane" data-pane="{i}"{"" if i == 0 else " hidden"}>{table_html(head, body) if body else t.get("text", "")}</div>'
    title = f'<h2>{esc(b["title"])}</h2>' if b.get('title') else '<h2>Стоимость работ</h2>'
    return f'<section class="sec dark"><div class="wrap">{title}<div class="panel"><div class="tabs" role="tablist">{nav}</div>{panes}</div></div></section>'


def b_steps(b, p):
    li = ''.join(f'<li><b>{esc(s["title"])}</b><span>{esc(s["text"])}</span></li>' for s in b['items'])
    return f'<section class="sec alt"><div class="wrap"><h2>{esc(b.get("title") or "Как мы работаем")}</h2><ol class="steps">{li}</ol></div></section>'


def form_html(title='', subtitle='', compact=False):
    return f'''<form class="lead-form{' compact' if compact else ''}" data-form>
{f'<h2>{esc(title)}</h2>' if title else ''}{f'<p>{esc(subtitle)}</p>' if subtitle else ''}
<div class="form-row">
<label><span>Телефон</span><input type="tel" name="phone" inputmode="tel" autocomplete="tel" placeholder="+375 (__) ___-__-__" required></label>
<label><span>Как удобнее</span><select name="how"><option>Принесу сам</option><option>Курьер</option><option>Выезд мастера</option></select></label>
<button class="btn" type="submit">Жду звонка</button></div>
<input type="hidden" name="service" value=""><input type="hidden" name="page" value="">
<small>Перезвоним за 5 минут в рабочее время. Нажимая кнопку, вы соглашаетесь с <a href="/privacy-policy/">обработкой персональных данных</a>.</small>
<div class="form-ok" hidden>Спасибо! Заявка принята — скоро перезвоним.</div></form>'''


def b_form(b, p):
    if not b.get('title') and not b.get('subtitle'):
        return f'<div class="wrap">{inline_cta()}</div>'
    ph = f'<img class="cta-photo" src="{esc(b["photo"])}" alt="" loading="lazy">' if b.get('photo') else ''
    return f'<section class="sec"><div class="wrap"><div class="cta-card{' has-photo' if ph else ''}">{form_html(b.get("title"), b.get("subtitle"))}{ph}</div></div></section>'


def inline_cta():
    return f'<div class="inline-cta"><span>Нужна консультация?</span>{phone_link("btn btn-ghost")}<button class="btn" data-open-form>Оставить заявку</button></div>'


def b_reviews(b, p):
    items = ''
    for r in b.get('items', [])[:8]:
        meta = ' · '.join(x for x in [r.get('date'), r.get('service')] if x)
        items += f'<figure class="card rev"><div class="stars" aria-label="5 из 5">★★★★★</div><blockquote>{esc(r["text"])}</blockquote><figcaption><b>{esc(r["name"])}</b> {esc(meta)}</figcaption></figure>'
    note = f'<p class="note">{b["note"]}</p>' if b.get('note') else f'<p class="note">Все отзывы — на <a href="{S["map_url"]}" rel="nofollow noopener" target="_blank">Яндекс Картах</a></p>'
    return f'<section class="sec alt"><div class="wrap"><h2>{esc(b.get("title") or "Отзывы")}</h2><div class="grid3">{items}</div>{note}</div></section>'


def b_faq(b, p):
    items = ''.join(f'<details><summary>{esc(x["q"])}</summary><div>{x["a"]}</div></details>' for x in b['items'])
    return f'<section class="sec"><div class="wrap"><h2>{esc(b.get("title") or "Вопрос — ответ").replace("Вопрос - ответ", "Вопрос — ответ")}</h2><div class="faq">{items}</div></div></section>'


def b_seo_text(b, p):
    return f'<section class="sec"><div class="wrap prose">{b["html"]}</div></section>'


def b_text(b, p):
    return f'<div class="wrap prose">{b["html"]}</div>'


def b_article(b, p):
    return f'<article class="wrap prose article">{b["html"]}</article>'


def b_heading(b, p):
    lvl = max(2, min(b['level'], 4))
    return f'<div class="wrap"><h{lvl}>{esc(b["text"])}</h{lvl}></div>'


def b_list(b, p):
    return '<div class="wrap prose"><ul>' + ''.join(f'<li>{esc(x)}</li>' for x in b['items']) + '</ul></div>'


def b_image(b, p):
    return f'<div class="wrap"><img class="pic" src="{esc(b["src"])}" alt="{esc(b.get("alt"))}" loading="lazy"></div>'


def b_html(b, p):
    return f'<div class="wrap">{b["html"]}</div>'


def b_cta(b, p):
    return f'<div class="wrap">{inline_cta()}</div>'


def b_stat(b, p):
    return ''


RENDER = {k[2:]: v for k, v in globals().items() if k.startswith('b_')}


def brands_block():
    a = ''.join(f'<a class="chip" href="{url(x["url"])}">{esc(x["title"])}</a>' for x in S['brands'])
    return f'<section class="sec"><div class="wrap"><h2>Выберите бренд телефона</h2><div class="chips">{a}</div><p class="note">Нет вашего бренда? Ремонтируем и его — позвоните {phone_link("link")}.</p></div></div></div></section>'


def special(p):
    """Блоки, которых не было в WordPress, но они нужны конкретным страницам."""
    extra = {}
    if p['path'] == '/remont-telefonov/':
        extra['after_hero'] = brands_block()
    if p['path'] == '/otzyvy/':
        extra['body'] = (f'<div class="wrap"><div class="sw-app" data-app="{S["smartwidgets_app"]}"></div>'
                         f'<script src="https://res.smartwidgets.ru/app.js" defer></script>'
                         f'<p class="note">Все отзывы — на <a href="{S["map_url"]}" rel="nofollow noopener" target="_blank">Яндекс Картах</a></p></div>')
    if p['path'] == '/kontakty/':
        hrs = ''.join(f'<li><b>{esc(a)}:</b> {esc(b)}</li>' for a, b in S['hours_detail'])
        extra['body'] = f'''<section class="sec"><div class="wrap contacts">
<div><h2>Как нас найти</h2><ul class="clean">
<li><b>Адрес:</b> {esc(S["address"])} · <a href="{S["map_url"]}" target="_blank" rel="noopener">маршрут в Яндекс Картах</a></li>
<li><b>Телефон:</b> {phone_link("link")}</li>
<li><b>E-mail:</b> <a href="mailto:{S["email"]}">{S["email"]}</a></li>{hrs}</ul>
{form_html("Перезвоним за 5 минут", "Оставьте номер — уточним детали и назовём цену.", compact=True)}</div>
<div class="map"><script type="text/javascript" charset="utf-8" async src="https://api-maps.yandex.ru/services/constructor/1.0/js/?um={S["yandex_map_um"]}&amp;width=100%25&amp;height=420&amp;lang=ru_RU&amp;scroll=false"></script></div>
</div></section>'''
    return extra


# ---------- schema.org ----------
def org_schema():
    return {
        "@context": "https://schema.org", "@type": "ElectronicsRepair", "@id": BASE + "/#org",
        "name": S['name'], "alternateName": ["Kepler", "Кеплер-центр"], "url": BASE + "/",
        "logo": BASE + S['logo'], "image": BASE + S['logo'], "telephone": S['phone'], "email": S['email'],
        "priceRange": "от 15 BYN",
        "address": {"@type": "PostalAddress", "streetAddress": S['street'], "addressLocality": S['city'],
                    "addressRegion": S['region'], "postalCode": S['postal'], "addressCountry": "BY"},
        "openingHoursSpecification": [{"@type": "OpeningHoursSpecification",
                                       "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                                       "opens": "09:00", "closes": "21:00"}],
        "areaServed": {"@type": "City", "name": S['city']}, "hasMap": S['map_url'],
        "sameAs": [x for x in [S['vk'], S['instagram'], S['tiktok']] if x]}


def crumbs(p):
    parts = [x for x in p['path'].strip('/').split('/') if x]
    trail = [('Главная', '/')]
    acc = '/'
    for x in parts:
        acc += x + '/'
        q = PAGES.get(acc)
        if acc == '/category/vse-stati/' or acc == '/vse-stati/':
            trail.append(('Полезные статьи', '/category/vse-stati/'))
            continue
        trail.append((h1_of(q) if q else x, acc))
    return trail


def schemas(p, trail):
    out = [org_schema()]
    if p['path'] != '/':
        out.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, **({"item": abs_url(u)} if i < len(trail) - 1 else {})}
            for i, (n, u) in enumerate(trail)]})
    faq = [x for b in p['blocks'] if b['type'] == 'faq' for x in b['items']]
    if faq:
        out.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": x['q'],
             "acceptedAnswer": {"@type": "Answer", "text": re.sub(r'<[^>]+>', ' ', x['a']).strip()}} for x in faq]})
    offers = []
    for b in p['blocks']:
        rows = b.get('rows', []) if b['type'] == 'table' else []
        for r in rows:
            if len(r) >= 2:
                m = re.search(r'(\d+(?:[.,]\d+)?)', r[-1])
                if m:
                    offers.append({"@type": "Offer", "price": m.group(1).replace(',', '.'), "priceCurrency": "BYN",
                                   "itemOffered": {"@type": "Service", "name": r[0]}})
    if offers and p['type'] == 'page':
        out.append({"@context": "https://schema.org", "@type": "Service", "name": h1_of(p),
                    "provider": {"@id": BASE + "/#org"}, "areaServed": {"@type": "City", "name": S['city']},
                    "hasOfferCatalog": {"@type": "OfferCatalog", "name": "Цены: " + h1_of(p), "itemListElement": offers[:40]}})
    if p['type'] == 'post':
        out.append({"@context": "https://schema.org", "@type": "Article", "headline": h1_of(p),
                    "datePublished": p.get('date'), "dateModified": p.get('modified'),
                    "author": {"@id": BASE + "/#org"}, "publisher": {"@id": BASE + "/#org"},
                    "mainEntityOfPage": abs_url(p['path'])})
    return ''.join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in out)


# ---------- каркас ----------
def nav_html():
    items = ''
    for g in S['nav']:
        if g.get('children'):
            sub = ''.join(f'<li><a href="{url(c["url"])}">{esc(c["title"])}</a></li>' for c in g['children'])
            items += f'<li class="dd"><a href="{url(g["url"])}">{esc(g["title"])}</a><ul>{sub}</ul></li>'
        else:
            items += f'<li><a href="{url(g["url"])}">{esc(g["title"])}</a></li>'
    return items


def layout(p, body, title, desc, trail):
    canon = abs_url(p['path'])
    bc = ''
    if p['path'] != '/':
        bc = '<nav class="bc wrap" aria-label="Хлебные крошки">' + ' › '.join(
            (f'<a href="{url(u)}">{esc(n)}</a>' if i < len(trail) - 1 else f'<span>{esc(n)}</span>')
            for i, (n, u) in enumerate(trail)) + '</nav>'
    ym = ''
    if S.get('yandex_metrika'):
        ym = f'<script>(function(m,e,t,r,i,k,a){{m[i]=m[i]||function(){{(m[i].a=m[i].a||[]).push(arguments)}};m[i].l=1*new Date();k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)}})(window,document,"script","https://mc.yandex.ru/metrika/tag.js","ym");ym({S["yandex_metrika"]},"init",{{clickmap:true,trackLinks:true,accurateTrackBounce:true,webvisor:true}});</script>'
    noindex = '<meta name="robots" content="noindex">' if (p.get('noindex') or BASE != S['domain']) else ''
    og_img = (p.get('seo') or {}).get('og_image') or BASE + S['logo']
    foot_links = ''.join(f'<li><a href="{url(x["url"])}">{esc(x["title"])}</a></li>' for x in S['footer_links'])
    svc_links = ''.join(f'<li><a href="{url(c["url"])}">{esc(c["title"])}</a></li>' for c in S['nav'][0]['children'])
    return f'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">{noindex}
<link rel="canonical" href="{canon}">
<meta property="og:type" content="{'article' if p['type'] == 'post' else 'website'}"><meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{canon}">
<meta property="og:image" content="{esc(og_img)}"><meta property="og:locale" content="ru_RU"><meta property="og:site_name" content="Кеплер">
<link rel="icon" href="https://kepler.by/wp-content/uploads/2026/04/cropped-%D0%BB%D0%BE%D0%B3%D0%BE%D1%82%D0%B8%D0%BF3-32x32.jpg" sizes="32x32"><link rel="apple-touch-icon" href="https://kepler.by/wp-content/uploads/2026/04/cropped-%D0%BB%D0%BE%D0%B3%D0%BE%D1%82%D0%B8%D0%BF3-180x180.jpg">
<link rel="stylesheet" href="/assets/style.css">
{schemas(p, trail)}{ym}
</head><body>
<div class="topbar"><div class="wrap"><a href="{S["map_url"]}" target="_blank" rel="noopener">{esc(S["address"])}</a><span>{esc(S["hours"])}</span></div></div>
<header class="hdr"><div class="wrap">
<a class="logo" href="/"><img src="{S["logo"]}" alt="Кеплер — ремонт техники в Гомеле" width="132" height="40"></a>
<button class="burger" aria-label="Меню" aria-expanded="false" data-burger><span></span></button>
<nav class="nav" data-nav><ul>{nav_html()}</ul></nav>
{phone_link("btn btn-sm hdr-phone")}
</div></header>
{bc}
<main>{body}</main>
<footer class="ftr"><div class="wrap fgrid">
<div><img src="{S["logo"]}" alt="Кеплер" width="132" height="40" loading="lazy"><p>{esc(S["address"])}<br>{esc(S["hours"])}</p><p>{phone_link("link")}<br><a href="mailto:{S["email"]}">{S["email"]}</a></p></div>
<div><h3>Ремонт техники</h3><ul>{svc_links}</ul></div>
<div><h3>Компания</h3><ul>{foot_links}</ul></div>
</div><div class="wrap legal">© {datetime.date.today().year} «Кеплер». {esc(S["legal"])}. Информация на сайте не является публичной офертой.</div></footer>
<div class="mbar"><a href="tel:{S["phone"]}" data-goal="click_phone">Позвонить</a><a href="{S["viber"]}" data-goal="click_viber">Viber</a>{f'<a href="{S["telegram"]}" data-goal="click_telegram">Telegram</a>' if S.get("telegram") else ''}<button data-open-form>Заявка</button></div>
<dialog class="modal" data-modal><button class="x" data-close aria-label="Закрыть">×</button>{form_html("Узнайте цену и срок ремонта", "Перезвоним за 5 минут в рабочее время (9:00–21:00).")}</dialog>
<script>window.KEPLER={{form:"https://formsubmit.co/ajax/{S["form_email"]}",ym:"{S.get("yandex_metrika", "")}"}};</script>
<script src="/assets/app.js" defer></script>
</body></html>'''


def render_page(p):
    trail = crumbs(p)
    extra = special(p)
    parts = []
    blocks = p['blocks']
    if not any(b['type'] == 'hero' for b in blocks):
        if p['type'] == 'post':
            date = (p.get('date') or '')[:10]
            parts.append(f'<section class="hero-wrap"><div class="wrap"><div class="hero hero-sm"><div class="hero-txt"><h1>{esc(h1_of(p))}</h1><p class="muted">Полезные статьи · {date}</p></div></div></div></section>')
        else:
            parts.append(f'<section class="hero-wrap"><div class="wrap"><div class="hero hero-sm"><div class="hero-txt"><h1>{esc(h1_of(p))}</h1></div></div></div></section>')
        if extra.get('after_hero'):
            parts.append(extra['after_hero'])
    seen_form = 0
    for b in blocks:
        if b['type'] == 'form' and (b.get('title') or b.get('subtitle')):
            seen_form += 1
        fn = RENDER.get(b['type'])
        if not fn:
            continue
        parts.append(fn(b, p))
        if b['type'] == 'hero' and extra.get('after_hero'):
            parts.append(extra['after_hero'])
    if extra.get('body'):
        parts.append(extra['body'])
    if p['type'] == 'post':
        parts.append(f'<section class="sec"><div class="wrap"><div class="cta-card">{form_html("Нужен ремонт?", "Бесплатная диагностика при заказе ремонта, гарантия " + S["warranty"] + ".")}</div></div></section>')
        parts.append(related_posts(p))
    elif not seen_form and p['path'] not in ('/kontakty/', '/privacy-policy/', '/rekvizity/'):
        parts.append(f'<section class="sec"><div class="wrap"><div class="cta-card">{form_html("Остались вопросы?", "Оставьте номер — перезвоним и всё расскажем.")}</div></div></section>')
    seo = p.get('seo') or {}
    title = no_bang(seo.get('title') or h1_of(p))
    title = title.replace('Росо', 'Poco')
    desc = seo.get('description') or ''
    if not desc:
        txts = [re.sub('<[^>]+>', ' ', b.get('html', '')) for b in blocks if b['type'] in ('text', 'article', 'seo_text')]
        desc = re.sub(r'\s+', ' ', ' '.join(txts)).strip()[:155]
    return layout(p, '\n'.join(parts), title, desc, trail)


def posts():
    return sorted([p for p in PAGES.values() if p['type'] == 'post'], key=lambda x: x.get('date') or '', reverse=True)


def related_posts(p):
    lst = [x for x in posts() if x['path'] != p['path']][:3]
    cards = ''.join(f'<a class="card post" href="{url(x["path"])}"><b>{esc(h1_of(x))}</b><span class="muted">{(x.get("date") or "")[:10]}</span></a>' for x in lst)
    return f'<section class="sec"><div class="wrap"><h2>Ещё статьи</h2><div class="grid3">{cards}</div></div></section>'


def category_page():
    cards = ''
    for x in posts():
        first = next((b for b in x['blocks'] if b['type'] == 'article'), None)
        ex = re.sub(r'\s+', ' ', re.sub('<[^>]+>', ' ', first['html'] if first else '')).strip()[:180]
        cards += f'<a class="card post" href="{url(x["path"])}"><b>{esc(h1_of(x))}</b><p>{esc(ex)}…</p><span class="muted">{(x.get("date") or "")[:10]}</span></a>'
    p = {'path': '/category/vse-stati/', 'type': 'page', 'title': 'Полезные статьи о ремонте техники', 'blocks': [],
         'seo': {'title': 'Полезные статьи о ремонте техники | Кеплер, Гомель',
                 'description': 'Советы мастеров сервисного центра Кеплер: что делать, если сломался компьютер, телевизор, принтер или ноутбук.'}}
    trail = [('Главная', '/'), ('Полезные статьи', '/category/vse-stati/')]
    body = f'<section class="hero-wrap"><div class="wrap"><div class="hero hero-sm"><div class="hero-txt"><h1>Полезные статьи</h1></div></div></div></section><section class="sec"><div class="wrap"><div class="grid3">{cards}</div></div></section>'
    return p, layout(p, body, p['seo']['title'], p['seo']['description'], trail)


def preview_fix(h):
    """Превью с диска: корневые ссылки → file:///…, логотип со старого сайта."""
    def rep(m):
        attr, path = m.group(1), m.group(2)
        if path.startswith(PREFIX):
            return m.group(0)
        tail = 'index.html' if INDEX and path.endswith('/') else ''
        return f'{attr}="{PREFIX}{path}{tail}"'
    return re.sub(r'(href|src)="(/(?!/)[^"]*)"', rep, h)


HAS_LOCAL_IMG = os.path.isdir(os.path.join(ROOT, 'wp-content'))


def localize(h):
    """Картинки WordPress лежат в репозитории по тем же путям: /wp-content/uploads/…"""
    if HAS_LOCAL_IMG:
        h = h.replace('https://kepler.by/wp-content/uploads/', '/wp-content/uploads/')
    else:
        h = h.replace('"/assets/logo.png"', '"https://kepler.by/wp-content/uploads/2023/03/logo.png"')
    return h


def write(path, content):
    content = localize(content)
    if PREFIX:
        content = preview_fix(content)
    d = os.path.join(DIST, path.strip('/'))
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(content)


def main():
    if os.path.exists(DIST):
        shutil.rmtree(DIST)
    shutil.copytree(os.path.join(ROOT, 'assets'), os.path.join(DIST, 'assets'))
    if HAS_LOCAL_IMG:
        shutil.copytree(os.path.join(ROOT, 'wp-content'), os.path.join(DIST, 'wp-content'))
        logo = os.path.join(ROOT, 'wp-content/uploads/2023/03/logo.png')
        if os.path.exists(logo):
            shutil.copy(logo, os.path.join(DIST, 'assets/logo.png'))
    urls = []
    for p in PAGES.values():
        write(p['path'], render_page(p))
        urls.append((p['path'], (p.get('modified') or TODAY)[:10], p))
    cp, chtml = category_page()
    write(cp['path'], chtml)
    urls.append((cp['path'], TODAY, cp))
    # 404
    p404 = {'path': '/404/', 'type': 'page', 'title': 'Страница не найдена', 'blocks': [], 'noindex': True, 'seo': {}}
    body = f'<section class="hero-wrap"><div class="wrap"><div class="hero hero-sm"><div class="hero-txt"><h1>Страница не найдена</h1><p>Возможно, её перенесли. Начните с <a href="/">главной</a> или позвоните — {phone_link("link")}.</p></div></div></div></section>'
    with open(os.path.join(DIST, '404.html'), 'w', encoding='utf-8') as f:
        h404 = localize(layout(p404, body, 'Страница не найдена — Кеплер', '', [('Главная', '/'), ('404', '/404/')]))
        f.write(preview_fix(h404) if PREFIX else h404)
    # sitemap и robots
    sm = ''.join(f'<url><loc>{abs_url(u)}</loc><lastmod>{d}</lastmod><priority>{"1.0" if u == "/" else ("0.8" if p["type"] == "page" else "0.6")}</priority></url>'
                 for u, d, p in sorted(urls, key=lambda x: x[0]) if not p.get('noindex'))
    open(os.path.join(DIST, 'sitemap.xml'), 'w', encoding='utf-8').write(
        f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>')
    if BASE != S['domain']:  # тестовая копия не индексируется
        open(os.path.join(DIST, 'robots.txt'), 'w').write('User-agent: *\nDisallow: /\n')
    else:
        open(os.path.join(DIST, 'robots.txt'), 'w').write(f'User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n')
    if os.path.exists(os.path.join(ROOT, 'CNAME')):
        shutil.copy(os.path.join(ROOT, 'CNAME'), os.path.join(DIST, 'CNAME'))
    open(os.path.join(DIST, '.nojekyll'), 'w').write('')
    print('страниц:', len(urls), '→', DIST)


if __name__ == '__main__':
    main()
