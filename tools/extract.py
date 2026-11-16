"""Разбирает выгрузку WordPress (kepler-export.json) в content/pages/*.json.

Каждая страница превращается в список смысловых блоков: hero, problems, table,
steps, form, reviews, text, faq, list, image, html. Шаблон сайта рисует их сам,
поэтому в JSON остаётся только содержимое, без вёрстки Elementor.
"""
import json, re, sys, os
from urllib.parse import unquote, urlparse
from bs4 import BeautifulSoup, NavigableString

SRC = sys.argv[1] if len(sys.argv) > 1 else 'src/kepler-export.json'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'content'

E = json.load(open(SRC, encoding='utf-8'))
HOST = 'https://kepler.by'

ALLOWED = {'p', 'br', 'strong', 'b', 'em', 'i', 'ul', 'ol', 'li', 'a', 'h2', 'h3', 'h4',
           'table', 'thead', 'tbody', 'tr', 'td', 'th', 'blockquote', 'img', 'span'}


def path_of(url):
    p = urlparse(url).path
    return unquote(p) if p else '/'


def clean_html(el):
    """Оставляет простую разметку: абзацы, списки, ссылки, жирный."""
    if el is None:
        return ''
    el = BeautifulSoup(str(el), 'lxml')
    for t in el.find_all(['script', 'style', 'svg', 'button', 'form', 'noscript']):
        t.decompose()
    for t in el.find_all(True):
        if t.name not in ALLOWED:
            t.unwrap()
            continue
        keep = {}
        if t.name == 'a' and t.get('href'):
            h = t['href']
            if h.startswith(HOST):
                h = path_of(h)
            keep['href'] = h
        if t.name == 'img' and t.get('src'):
            keep['src'] = t['src']
            keep['alt'] = t.get('alt', '')
        t.attrs = keep
    for t in el.find_all('span'):
        t.unwrap()
    body = el.body or el
    html = ''.join(str(c) for c in body.contents)
    html = re.sub(r'\s+', ' ', html)
    html = re.sub(r'<p>\s*(&nbsp;|\xa0)?\s*</p>', '', html)
    return html.strip()


def txt(el):
    return re.sub(r'\s+', ' ', el.get_text(' ', strip=True)).strip() if el else ''


def is_hidden_mobile_dup(el):
    cls = ' '.join(el.get('class', []))
    return 'elementor-hidden-desktop' in cls and 'elementor-hidden-tablet' in cls


def widget_blocks(w):
    t = w.get('data-widget_type', '').split('.')[0]
    if t == 'heading':
        h = w.find(re.compile('^h[1-6]$'))
        lvl = int(h.name[1]) if h else 2
        return [{'type': 'heading', 'level': lvl, 'text': txt(w)}]
    if t == 'text-editor':
        html = clean_html(w.select_one('.elementor-widget-container') or w)
        return [{'type': 'text', 'html': html}] if html else []
    if t == 'icon-list':
        items = [txt(li) for li in w.select('li')]
        items = [i for i in items if i]
        return [{'type': 'list', 'items': items}] if items else []
    if t == 'image':
        img = w.find('img')
        if img and img.get('src'):
            return [{'type': 'image', 'src': img['src'], 'alt': img.get('alt', '')}]
        return []
    if t == 'image-box':
        title = txt(w.select_one('.elementor-image-box-title'))
        desc = txt(w.select_one('.elementor-image-box-description'))
        return [{'type': 'stat', 'label': title, 'value': desc}]
    if t == 'wpr-data-table':
        rows = []
        for tr in w.select('tr'):
            cells = [txt(c) for c in tr.find_all(['td', 'th'])]
            cells = [c for c in cells if c and c not in ('Заказать ремонт', 'Заказать услугу', 'Заказать')]
            if cells:
                rows.append(cells)
        if rows and len(rows[0]) >= 2 and re.search(r'Поломка|Услуга|Наименование|Неисправ', rows[0][0]):
            head, rows = rows[0], rows[1:]
        else:
            head = []
        return [{'type': 'table', 'head': head, 'rows': rows}] if rows else []
    if t == 'wpr-posts-timeline':
        steps = []
        for it in w.select('.wpr-timeline-entry, .wpr-story-info, .wpr-timeline-story'):
            pass
        text = txt(w)
        # «01 Заголовок Заголовок Текст 02 ...»
        parts = re.split(r'\b0(\d)\s+', text)
        for i in range(1, len(parts) - 1, 2):
            chunk = parts[i + 1].strip()
            words = chunk.split(' ')
            # заголовок повторяется дважды: ищем самый длинный повтор в начале
            title = ''
            for n in range(1, 8):
                a = ' '.join(words[:n]); b = ' '.join(words[n:2 * n])
                if a == b:
                    title = a; rest = ' '.join(words[2 * n:])
            if not title:
                title, rest = words[0], ' '.join(words[1:])
            steps.append({'title': title, 'text': rest})
        return [{'type': 'steps', 'items': steps}] if steps else []
    if t == 'form':
        return [{'type': 'form'}]
    if t == 'reviews':
        revs = []
        for s in w.select('.swiper-slide, .elementor-testimonial'):
            service = txt(s.select_one('.elementor-testimonial__name'))
            who = txt(s.select_one('.elementor-testimonial__title'))
            body = txt(s.select_one('.elementor-testimonial__text'))
            name, _, date = who.partition(', ')
            if body and (name, body) not in [(r['name'], r['text']) for r in revs]:
                revs.append({'name': name, 'date': date, 'service': service, 'text': body})
        return [{'type': 'reviews', 'items': revs}]
    if t == 'jet-unfold':
        html = clean_html(w.select_one('.jet-unfold__content-inner') or w.select_one('.jet-unfold__content') or w)
        return [{'type': 'seo_text', 'html': html}] if html else []
    if t in ('wpr-advanced-accordion', 'accordion', 'toggle'):
        faq = []
        for item in w.select('.wpr-accordion-item-wrap, .elementor-accordion-item, .elementor-toggle-item'):
            q = txt(item.select_one('.wpr-acc-title-text, .elementor-tab-title, .wpr-acc-button'))
            a = clean_html(item.select_one('.wpr-acc-panel-content, .elementor-tab-content, .wpr-acc-panel'))
            if q:
                faq.append({'q': q, 'a': a})
        return [{'type': 'faq', 'items': faq}] if faq else []
    if t == 'html':
        return [{'type': 'html', 'html': str(w.select_one('.elementor-widget-container') or w)}]
    if t == 'wpr-feature-list':
        items = [txt(x) for x in w.select('.wpr-feature-list-title, .wpr-feature-list-content-wrap')]
        items = [i for i in items if i]
        return [{'type': 'list', 'items': items}] if items else []
    if t == 'call-to-action':
        return [{'type': 'cta', 'title': txt(w.select_one('.elementor-cta__title')),
                 'text': txt(w.select_one('.elementor-cta__description'))}]
    if t == 'theme-post-content':
        return [{'type': 'article', 'html': clean_html(w)}]
    if t == 'elementskit-simple-tab':
        tabs = []
        titles = [txt(x) for x in w.select('.elementkit-tab-nav .elementskit-tab-title, .elementkit-nav-link')]
        panes = w.select('.elementkit-tab-pane, .tab-pane')
        for i, p in enumerate(panes):
            rows = []
            for tr in p.select('tr'):
                cells = [txt(c) for c in tr.find_all(['td', 'th'])]
                cells = [c for c in cells if c and c not in ('Заказать ремонт', 'Заказать услугу')]
                if cells:
                    rows.append(cells)
            tabs.append({'title': titles[i] if i < len(titles) else '', 'rows': rows,
                         'text': '' if rows else clean_html(p)})
        return [{'type': 'tabs', 'items': tabs}]
    if t in ('button', 'jet-view-more', 'spacer', 'divider', 'theme-post-title', 'post-info', 'breadcrumbs', 'post-navigation', 'posts', 'theme-post-featured-image'):
        return []
    return [{'type': 'unknown', 'widget': t, 'text': txt(w)[:300]}]


def collect(el, out):
    """Обходит дерево Elementor по порядку, пропуская мобильные дубли."""
    for c in el.find_all(recursive=False):
        if is_hidden_mobile_dup(c):
            continue
        if c.get('data-widget_type'):
            out.extend(widget_blocks(c))
        else:
            collect(c, out)


def merge(blocks):
    """Склеивает типовые узоры Elementor в смысловые блоки."""
    res = []
    i = 0
    while i < len(blocks):
        b = blocks[i]
        # Hero: H1 + список + статы
        if b['type'] == 'heading' and b['level'] == 1:
            hero = {'type': 'hero', 'h1': b['text'], 'bullets': [], 'stats': []}
            j = i + 1
            while j < len(blocks) and blocks[j]['type'] in ('list', 'stat') and j < i + 8:
                if blocks[j]['type'] == 'list':
                    items = [x for x in blocks[j]['items'] if not re.match(r'^\+?[\d\s()-]{9,}$', x)]
                    hero['bullets'] += items
                else:
                    hero['stats'].append({'label': blocks[j]['label'], 'value': blocks[j]['value']})
                j += 1
            res.append(hero); i = j; continue
        # Карточка поломки: heading(h3) [+image] + text «Признак поломки» + text + text «Цена ремонта» + text
        if b['type'] == 'heading' and i + 3 < len(blocks) and blocks[i + 1]['type'] in ('image', 'text'):
            seq = blocks[i + 1:i + 7]
            texts = [x for x in seq if x['type'] == 'text']
            plain = [re.sub('<[^>]+>', '', x['html']).strip() for x in texts]
            if len(plain) >= 4 and plain[0].startswith('Признак') and plain[2].startswith('Цена'):
                img = next((x for x in seq[:2] if x['type'] == 'image'), None)
                card = {'title': b['text'], 'symptom': plain[1], 'price': plain[3],
                        'image': img['src'] if img else ''}
                if res and res[-1]['type'] == 'problems':
                    res[-1]['items'].append(card)
                else:
                    res.append({'type': 'problems', 'items': [card]})
                i += 1 + (1 if img else 0) + 4
                continue
        res.append(b); i += 1
    # заголовок секции перед problems/table/steps/faq/reviews уходит в блок как title
    out = []
    for b in res:
        if out and out[-1]['type'] == 'heading' and out[-1]['level'] == 2 and \
                b['type'] in ('problems', 'table', 'steps', 'faq', 'reviews', 'tabs'):
            b['title'] = out.pop()['text']
        out.append(b)
    return out


def plain(b):
    return re.sub(r'<[^>]+>', '', b.get('html', '')).strip() if b['type'] == 'text' else ''


JUNK_TEXT = re.compile(r'^(Описание услуги|Версии windows|Нажимая кнопку.*|ㅤ)$', re.I)
PRICE = re.compile(r'^(от|ОТ)\s*\d')


def tidy(blocks):
    out = []
    i = 0
    n = len(blocks)
    while i < n:
        b = blocks[i]
        # мусор
        if b['type'] == 'text' and JUNK_TEXT.match(plain(b)):
            i += 1; continue
        if b['type'] == 'html' and not re.sub(r'<[^>]+>|\s', '', b['html']) and '<iframe' not in b['html']:
            i += 1; continue
        if b['type'] == 'list':
            b['items'] = [x for x in b['items'] if x.strip('ㅤ ').strip()]
            if not b['items']:
                i += 1; continue
        if b['type'] == 'cta' and not (b.get('title') or b.get('text')):
            i += 1; continue
        # статы и телефон сразу после hero
        if b['type'] == 'stat' and out and out[-1]['type'] in ('hero',) or \
                (b['type'] == 'stat' and len(out) >= 2 and out[-2]['type'] == 'hero' and out[-1]['type'] == 'text'):
            hero = out[-1] if out[-1]['type'] == 'hero' else out[-2]
            hero['stats'].append({'label': b['label'], 'value': b['value']})
            i += 1; continue
        if b['type'] == 'text' and out and out[-1]['type'] == 'hero' and not out[-1].get('lead'):
            out[-1]['lead'] = b['html']; i += 1; continue
        if b['type'] == 'list' and out and out[-1]['type'] == 'hero' and all(re.match(r'^\+?[\d\s()-]{9,}$', x) for x in b['items']):
            i += 1; continue
        # карточка услуги: h3 + [image] + текст(ы) + цена
        if b['type'] == 'heading' and b['level'] == 3:
            j = i + 1; card = {'title': b['text'], 'price': '', 'points': [], 'desc': '', 'image': ''}
            while j < n and j < i + 8 and blocks[j]['type'] in ('text', 'list', 'image'):
                x = blocks[j]
                if x['type'] == 'image' and not card['image']:
                    card['image'] = x['src']
                elif x['type'] == 'list':
                    card['points'] += x['items']
                elif x['type'] == 'text':
                    t = plain(x)
                    if JUNK_TEXT.match(t) or t in ('Цена услуги', 'не работает:'):
                        pass
                    elif PRICE.match(t):
                        card['price'] = t
                        j += 1
                        break
                    else:
                        card['desc'] = (card['desc'] + ' ' + t).strip()
                j += 1
            if card['price']:
                # хвост из списка после цены (главная: цена, потом признаки)
                while j < n and blocks[j]['type'] == 'list':
                    card['points'] += [p for p in blocks[j]['items'] if p.strip('ㅤ ').strip()]
                    j += 1
                if out and out[-1]['type'] == 'services':
                    out[-1]['items'].append(card)
                else:
                    sv = {'type': 'services', 'items': [card]}
                    if out and out[-1]['type'] == 'heading' and out[-1]['level'] == 2:
                        sv['title'] = out.pop()['text']
                    out.append(sv)
                i = j; continue
        # форма: [text «Закажите…» | «Остались вопросы?»] [list подзаголовок] form
        is_cta_text = b['type'] == 'text' and len(plain(b)) < 110 and re.search(r'Закажите|Остались|вопрос|скидк|Нужна', plain(b))
        if b['type'] == 'form' or (is_cta_text and i + 2 < n and
                                   blocks[i + 1]['type'] == 'list' and blocks[i + 2]['type'] == 'form') or \
                (is_cta_text and i + 1 < n and blocks[i + 1]['type'] == 'form'):
            form = {'type': 'form', 'title': '', 'subtitle': ''}
            j = i
            if blocks[j]['type'] == 'text':
                form['title'] = plain(blocks[j]); j += 1
            if j < n and blocks[j]['type'] == 'list':
                form['subtitle'] = ' '.join(blocks[j]['items']); j += 1
            j += 1  # сама форма
            if out and out[-1]['type'] == 'text' and not form['title'] and len(plain(out[-1])) < 110 and re.search(r'Закажите|скидк', plain(out[-1])):
                form['title'] = plain(out.pop())
            out.append(form); i = j; continue
        # отзывы: heading «Отзывы» + text «Более … отзывов» + reviews
        if b['type'] == 'reviews':
            if out and out[-1]['type'] == 'text' and 'отзыв' in plain(out[-1]).lower():
                b['note'] = out.pop()['html']
            if out and out[-1]['type'] == 'heading':
                b['title'] = out.pop()['text']
            out.append(b); i += 1; continue
        # «Вопрос – ответ» заголовок + faq
        if b['type'] == 'faq' and out and out[-1]['type'] == 'heading':
            b['title'] = out.pop()['text']
        # одиночная цена после problems — дубль первой карточки
        if b['type'] == 'text' and out and out[-1]['type'] == 'problems' and PRICE.match(plain(b)):
            i += 1; continue
        out.append(b); i += 1
    # склеиваем подряд идущие problems
    res = []
    for b in out:
        if res and b['type'] == 'problems' and res[-1]['type'] == 'problems':
            res[-1]['items'] += b['items']
        else:
            res.append(b)
    # «Вопрос-ответ» заголовок без faq
    res = [b for k, b in enumerate(res) if not (b['type'] == 'heading' and re.match(r'Вопрос', b['text'])
                                                and (k + 1 >= len(res) or res[k + 1]['type'] != 'faq'))]
    return res


def page_record(it):
    s = BeautifulSoup(it['html'], 'lxml')
    main = s.select_one('[data-elementor-type=wp-page]') or s.select_one('[data-elementor-type=wp-post]') \
        or s.select_one('[data-elementor-type=single]')
    raw = []
    if main:
        collect(main, raw)
    blocks = tidy(merge(raw))
    lds = [x.string for x in s.select('script[type="application/ld+json"]') if x.string]
    path = '/' if it['id'] == 1290 else path_of(it['link'])
    return {
        'id': it['id'], 'type': it['type'], 'path': path,
        'title': BeautifulSoup(it['title']['rendered'], 'lxml').get_text(),
        'seo': it['seo'], 'date': it.get('date'), 'modified': it.get('modified'),
        'parent': it.get('parent', 0), 'blocks': blocks,
    }


def slug_key(path):
    if path == '/':
        return 'index'
    return path.strip('/').replace('/', '__')


def main():
    os.makedirs(f'{OUT}/pages', exist_ok=True)
    unknown = {}
    for it in E['items']:
        rec = page_record(it)
        for b in rec['blocks']:
            if b['type'] == 'unknown':
                unknown.setdefault(b['widget'], []).append(rec['path'])
        with open(f"{OUT}/pages/{slug_key(rec['path'])}.json", 'w', encoding='utf-8') as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)
    json.dump(E['media'], open(f'{OUT}/media.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('pages:', len(E['items']))
    for k, v in unknown.items():
        print('unknown widget', k, len(v), v[:3])


if __name__ == '__main__':
    main()
