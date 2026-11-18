"""Докачивает отдельные страницы WordPress (POST, как wp_fetch.py) и их файлы.
Список — tools/extra-pages.txt: «адрес_на_сайте<TAB>запрос_к_WordPress». Запускается в workflow fetch-files."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import wp_fetch as W

meta_p = os.path.join(W.OUT, 'pages.json')
meta = json.load(open(meta_p, encoding='utf-8'))
for line in open('tools/extra-pages.txt', encoding='utf-8'):
    if not line.strip():
        continue
    path, src = line.rstrip('\n').split('\t')
    st, b = W.req(W.H + src, 'POST')
    print(st, len(b), path)
    if st == 200 and b'</html>' in b:
        W.save(os.path.join('html', path.strip('/'), 'index.html'), b)
        W.html_deps(b.decode('utf-8', 'ignore'))
        if not any(m['path'] == path for m in meta):
            meta.append({'path': path, 'src': W.H + src, 'modified': ''})
json.dump(meta, open(meta_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
