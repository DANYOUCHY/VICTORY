"""Manage blog posts on the static site.

  python3 tools/posts.py index              build data/posts.json from the site as it is now
  python3 tools/posts.py add post.json      add a new post (see NEW POST below)
  python3 tools/posts.py lists              rebuild the blog pages and the "recent posts"
                                            sidebar from data/posts.json

Every post is built from src/ (see src/README.md): its own small files are in
src/pages/posts/<slug>/ (title, date, image, content, navigation, comments, seo, page.json),
and the layout it shares with all posts is in src/components/post/. The blog pages and the
recent-posts sidebar are made by the build (tools/build) from data/posts.json.

NEW POST (post.json, UTF-8):
  {
    "slug": "my-new-post",                  address: /my-new-post/  (Hebrew is fine)
    "title": "כותרת הפוסט",
    "date": "2026-10-30",                   optional, default today
    "image": "path/to/image.jpg",           featured image
    "image_alt": "תיאור התמונה",            optional, default the title
    "content_html": "<p>...</p>",           the post body, as HTML
    "description": "...",                   optional, for search engines; default the excerpt
    "author": "יוחי דנחי"                   optional
  }

A new post's folder is made from the newest post's folder, so it has exactly the same
layout. Adding a post also updates the previous post's "next" link, data/posts.json,
every blog page and sidebar (by rebuilding the pages from src/) and the sitemaps.
If it fails half way: git checkout -- site data src  (and remove the new post's folder).
"""
import datetime
import html
import json
import os
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.build.__main__ import main as build_pages                      # noqa: E402
from tools.build.post_lists import (ARTICLE_CLASS, SIDEBAR_COUNT,           # noqa: E402
                                    blog_page_count, paragraph)
from tools.build.template import read_source                                # noqa: E402

ROOT = 'site'
DATA = 'data/posts.json'
POSTS_SRC = os.path.join('src', 'pages', 'posts')
BLOG_SRC = os.path.join('src', 'pages', 'blog')
POST_LAYOUT = 'components/post/page.html'
BASE = 'https://www.victory.org.il'
BLOG_WORDS, SIDEBAR_WORDS = 25, 20
MONTHS_HE = ['ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני', 'יולי', 'אוגוסט',
             'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר']
para = paragraph


# ---------- small HTML helpers (string based, so untouched parts stay byte for byte) ----------

def element_span(t, start):
    """(start, end) of the <div ...> element that begins at `start`, matching nested divs."""
    depth = 0
    for m in re.finditer(r'<(/?)div\b[^>]*>', t[start:]):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return start, start + m.end()
    raise ValueError('unbalanced div at %d' % start)

def widget_spans(t, widget_type):
    """Spans of every Elementor widget of this type."""
    out = []
    for m in re.finditer(r'data-widget_type="%s"' % re.escape(widget_type), t):
        s = t.rfind('<div class="elementor-element', 0, m.start())
        out.append(element_span(t, s))
    return out

def replace_widget_inner(t, span, inner):
    """Replace what is inside the widget's elementor-widget-container."""
    s, e = span
    c = t.find('<div class="elementor-widget-container">', s, e)
    cs, ce = element_span(t, c)
    open_tag = '<div class="elementor-widget-container">'
    return t[:cs] + open_tag + inner + '</div>' + t[ce:]

def text_of(fragment):
    return html.unescape(re.sub(r'<[^>]+>', ' ', fragment))

def words(s, n):
    w = s.split()
    return ' '.join(w[:n])

def attr(s):
    return html.escape(s, quote=True)

def root_paths(s):
    return re.sub(r'(?:\.\./)+(assets|wp-content|wp-includes)/', r'/\1/', s)

def page_file(url_path):
    return os.path.join(ROOT, urllib.parse.unquote(url_path).strip('/'), 'index.html')

def he_date(d):
    return '%s %d, %d' % (MONTHS_HE[d.month - 1], d.day, d.year)


# ---------- index ----------

def blog_pages():
    pages = [os.path.join(ROOT, 'blog', 'index.html')]
    n = 2
    while os.path.exists(os.path.join(ROOT, 'blog', str(n), 'index.html')):
        f = os.path.join(ROOT, 'blog', str(n), 'index.html')
        if 'data-widget_type="posts.classic"' not in open(f, encoding='utf-8').read():
            break  # an empty "nothing found" page after the last one
        pages.append(f)
        n += 1
    return pages

def parse_articles(t):
    out = []
    for m in re.finditer(r'<article class="(elementor-post[^"]*\bpost-(\d+)\b[^"]*)"[^>]*>(.*?)</article>', t, re.S):
        cls, a = m.group(1), m.group(3)
        url = re.search(r'<h3 class="elementor-post__title">\s*<a href="([^"]+)"', a).group(1)
        title = text_of(re.search(r'<h3 class="elementor-post__title">\s*<a[^>]*>(.*?)</a>', a, re.S).group(1)).strip()
        ex = re.search(r'<div class="elementor-post__excerpt">(.*?)</div>', a, re.S)
        img = re.search(r'<img [^>]*>', a)
        author = re.search(r'<span class="elementor-post-author">\s*(.*?)\s*</span>', a, re.S)
        out.append({'id': int(m.group(2)), 'cls': cls, 'url': url, 'title': title,
                    'excerpt_html': ex.group(1).strip() if ex else '',
                    'excerpt': text_of(ex.group(1)).strip() if ex else '',
                    'thumb': root_paths(img.group(0)) if img else '',
                    'author': author.group(1).strip() if author else ''})
    return out

def cmd_index():
    posts = []
    for f in blog_pages():
        t = open(f, encoding='utf-8').read()
        s, e = widget_spans(t, 'posts.classic')[0]
        posts += parse_articles(t[s:e])
    for p in posts:
        pf = page_file(p['url'])
        t = open(pf, encoding='utf-8').read() if os.path.exists(pf) else ''
        m = re.search(r'<time>\s*(\S+) (\d{1,2}), (\d{4})\s*</time>', t)
        p['date'] = ('%s-%02d-%02d' % (m.group(3), MONTHS_HE.index(m.group(1)) + 1, int(m.group(2)))
                     if m and m.group(1) in MONTHS_HE else '')
    # the sidebar shows a shorter excerpt; keep the ones the site already has
    t = open(page_file(posts[0]['url']), encoding='utf-8').read()
    side = {}
    for f in [page_file(p['url']) for p in posts[:SIDEBAR_COUNT + 1]]:
        st = open(f, encoding='utf-8').read()
        for a in parse_articles(st[slice(*widget_spans(st, 'posts.classic')[0])]):
            side[a['id']] = a['excerpt_html']
    for p in posts:
        p['excerpt_short_html'] = side.get(p['id']) or para(words(p['excerpt'], SIDEBAR_WORDS))
    os.makedirs(os.path.dirname(DATA), exist_ok=True)
    json.dump(posts, open(DATA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('posts indexed:', len(posts))



# ---------- the source files of a post (src/pages/posts/<slug>/) ----------

def post_folder(url_path):
    """Where a post's own files are, from its address."""
    return os.path.join(POSTS_SRC, urllib.parse.unquote(url_path).strip('/'))

def read_part(folder, name):
    return read_source(Path(folder) / name)

def write_part(folder, name, text):
    """A source file holds its text plus one final newline (see src/README.md)."""
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, name), 'w', encoding='utf-8', newline='\n') as f:
        f.write(text + '\n')

def read_page_json(folder):
    return json.load(open(os.path.join(folder, 'page.json'), encoding='utf-8'))

def write_page_json(folder, data):
    write_part(folder, 'page.json', json.dumps(data, ensure_ascii=False, indent=2))


# ---------- lists: the blog pages and the recent-posts sidebar ----------

def ensure_blog_pages(posts):
    """One src/pages/blog/<n>/ per blog page; a new last page is a copy of page 2 with its own number."""
    model_dir = os.path.join(BLOG_SRC, '2')
    for n in range(2, blog_page_count(posts) + 1):
        folder = os.path.join(BLOG_SRC, str(n))
        if os.path.exists(os.path.join(folder, 'page.json')):
            continue
        text = json.dumps(read_page_json(model_dir), ensure_ascii=False)
        text = text.replace('/blog/2/', '/blog/%d/' % n).replace('paged-2 ', 'paged-%d ' % n)
        data = json.loads(text)
        data['output'] = 'blog/%d/index.html' % n
        data['params']['blog_page'] = n
        write_page_json(folder, data)
        print('new blog page', n)

def build_all():
    """Rebuild every page from src/ (the lists come from data/posts.json)."""
    if build_pages([]) != 0:
        sys.exit('building the pages failed')

def cmd_lists():
    ensure_blog_pages(json.load(open(DATA, encoding='utf-8')))
    build_all()


# ---------- add ----------

def nav_inner(prev_p, next_p):
    def prev_html(p):
        return ('<a href="%s" rel="prev"><span class="post-navigation__arrow-wrapper post-navigation__arrow-prev">'
                '<i aria-hidden="true" class="fa fa-angle-right"></i><span class="elementor-screen-only">קודם</span></span>'
                '<span class="elementor-post-navigation__link__prev"><span class="post-navigation__prev--label">קודם</span>'
                '<span class="post-navigation__prev--title">%s</span></span></a>' % (p['url'], html.escape(p['title'], quote=False)))
    def next_html(p):
        return ('<a href="%s" rel="next"><span class="elementor-post-navigation__link__next"><span class="post-navigation__next--label">הבא</span>'
                '<span class="post-navigation__next--title">%s</span></span><span class="post-navigation__arrow-wrapper post-navigation__arrow-next">'
                '<i aria-hidden="true" class="fa fa-angle-left"></i><span class="elementor-screen-only">הבא</span></span></a>' % (p['url'], html.escape(p['title'], quote=False)))
    return ('\n\t\t\t\t\t<div class="elementor-post-navigation" role="navigation" aria-label="ניווט בין פוסטים">\n'
            '\t\t\t<div class="elementor-post-navigation__prev elementor-post-navigation__link">\n\t\t\t\t%s\t\t\t</div>\n'
            '\t\t\t\t\t\t<div class="elementor-post-navigation__separator-wrapper">\n'
            '\t\t\t\t<div class="elementor-post-navigation__separator"></div>\n\t\t\t</div>\n'
            '\t\t\t\t\t\t<div class="elementor-post-navigation__next elementor-post-navigation__link">\n\t\t\t\t%s\t\t\t</div>\n'
            '\t\t</div>\n\t\t\t\t') % (prev_html(prev_p) if prev_p else '', next_html(next_p) if next_p else '')

def navigation(old_inner, prev_p, next_p):
    """The "previous / next" links, keeping the arrow icons the post already uses (svg or font icon)."""
    prev_icon = re.search(r'post-navigation__arrow-prev">(.*?)<span class="elementor-screen-only">', old_inner, re.S)
    next_icon = re.search(r'post-navigation__arrow-next">(.*?)<span class="elementor-screen-only">', old_inner, re.S)
    inner = nav_inner(prev_p, next_p)
    inner = inner.replace('<i aria-hidden="true" class="fa fa-angle-right"></i>', prev_icon.group(1) if prev_icon else '')
    return inner.replace('<i aria-hidden="true" class="fa fa-angle-left"></i>', next_icon.group(1) if next_icon else '')

def save_images(src, slug, date):
    from PIL import Image
    im = Image.open(src).convert('RGB')
    w, h = im.size
    folder = os.path.join(ROOT, 'assets', 'wp', 'uploads', '%04d' % date.year, '%02d' % date.month)
    os.makedirs(folder, exist_ok=True)
    name = re.sub(r'[^\w֐-׿-]+', '-', slug).strip('-')[:60] or 'post'
    sizes = {}
    def save(box, label):
        c = im.copy()
        c.thumbnail(box)
        fn = '%s%s.webp' % (name, '' if label == 'full' else '-%dx%d' % c.size)
        c.save(os.path.join(folder, fn), 'WEBP', quality=82)
        sizes[label] = ('/' + os.path.relpath(os.path.join(folder, fn), ROOT).replace(os.sep, '/'), c.size)
    save((w, h), 'full')
    save((300, 300), 'medium')
    save((768, 100000), 'medium_large')
    save((1024, 1024), 'large')
    jpg = os.path.join(folder, name + '.jpg')
    im.save(jpg, 'JPEG', quality=88)  # for sharing previews (og:image)
    sizes['og'] = ('/' + os.path.relpath(jpg, ROOT).replace(os.sep, '/'), (w, h))
    return sizes

def srcset(sizes):
    return ', '.join('%s %dw' % (sizes[k][0], sizes[k][1][0]) for k in ('medium_large', 'medium', 'large', 'full'))

def seo_part(seo, url, title, description, alt, sizes):
    """The search and sharing tags (title, description, picture) of the new post."""
    seo = re.sub(r'<title>.*?</title>', '<title>%s</title>' % html.escape(title, quote=False), seo, count=1, flags=re.S)
    def meta(t, key, value, prop=True):
        k = 'property' if prop else 'name'
        return re.sub(r'(<meta %s="%s" content=")[^"]*(")' % (k, re.escape(key)), lambda m: m.group(1) + attr(value) + m.group(2), t)
    seo = meta(seo, 'description', description, prop=False)
    for k, v in (('og:url', BASE + url), ('og:title', title), ('og:description', description),
                 ('og:image', BASE + sizes['og'][0]), ('og:image:secure_url', BASE + sizes['og'][0]),
                 ('og:image:width', str(sizes['og'][1][0])), ('og:image:height', str(sizes['og'][1][1])),
                 ('og:image:alt', alt)):
        seo = meta(seo, k, v)
    for k, v in (('twitter:title', title), ('twitter:description', description), ('twitter:image', BASE + sizes['og'][0])):
        seo = meta(seo, k, v, prop=False)
    return re.sub(r'<link rel="canonical" href="[^"]*"', '<link rel="canonical" href="%s"' % (BASE + url), seo)

def image_part(sizes, alt):
    ml = sizes['medium_large']
    img = ('<img fetchpriority="high" width="%d" height="%d" src="%s" class="attachment-medium_large size-medium_large" '
           'alt="%s" srcset="%s" sizes="(max-width: %dpx) 100vw, %dpx" />') % (ml[1][0], ml[1][1], ml[0], attr(alt), srcset(sizes), ml[1][0], ml[1][0])
    return '\n' + '\t' * 14 + img + '\t' * 18

def comments_part(old, old_url, url, new_id):
    """The comment form of the new post; a new post starts with no comments."""
    seg = re.sub(r'<h3 class="comments-title">.*?</h3>', '', old, flags=re.S)
    seg = re.sub(r'<ol class="ast-comment-list">.*?</ol>|<ol class="comment-list">.*?</ol>', '', seg, flags=re.S)
    seg = re.sub(r"(name=['\"]comment_post_ID['\"] value=['\"])\d+", lambda m: m.group(1) + str(new_id), seg)
    seg = seg.replace(old_url + '#respond', url + '#respond')
    return re.sub(r'(name="page" value=")[^"]*', lambda m: m.group(1) + url, seg)

def post_params(old, new_id, url, title, sizes):
    """The new post's page.json values, from the newest post's. Links to "this page" use the new address."""
    p = dict(old)
    p['body_class'] = p['body_class'].replace('postid-%d' % old['post_id'], 'postid-%d' % new_id)
    p['post_class'] = re.sub(r'^post-\d+ ', 'post-%d ' % new_id, p['post_class'])
    p['post_id'] = new_id
    p['elementor_post'] = '{"id":%d,"title":"%s","excerpt":"","featuredImage":"%s"}' % (
        new_id, urllib.parse.quote(title), (BASE + sizes['large'][0]).replace('/', '\\/'))
    p['skip_href'], p['contact_href'] = url + '#content', url + '#contact'
    p['self_prefix'] = p['form_page'] = url
    p['featured_image'] = p['comments'] = 'on'
    return p

def post_entry(new_id, url, title, plain, alt, sizes, author, date):
    """The new post's line in data/posts.json (the blog pages and sidebars are built from it)."""
    medium = sizes['medium']
    thumb = ('<img fetchpriority="high" decoding="async" width="%d" height="%d" src="%s" class="attachment-medium size-medium" '
             'alt="%s" srcset="%s" sizes="(max-width: %dpx) 100vw, %dpx" />') % (
        medium[1][0], medium[1][1], medium[0], attr(alt), srcset(sizes), medium[1][0], medium[1][0])
    excerpt = words(plain, BLOG_WORDS)
    return {'id': new_id, 'url': url, 'title': title, 'excerpt': excerpt,
            'excerpt_html': paragraph(excerpt), 'excerpt_short_html': paragraph(words(plain, SIDEBAR_WORDS)),
            'cls': ARTICLE_CLASS % new_id, 'thumb': thumb, 'author': author, 'date': date.isoformat()}

def write_new_post(folder, newest_dir, newest, url, title, date, content, seo, alt, sizes, new_id):
    """All the files of the new post, made from the newest post's files."""
    old = read_page_json(newest_dir)
    write_part(folder, 'seo.html', seo)
    write_part(folder, 'title.html', re.sub(r'(<h1[^>]*>).*?(</h1>)', lambda m: m.group(1) + html.escape(title, quote=False) + m.group(2),
                                            read_part(newest_dir, 'title.html'), count=1, flags=re.S))
    write_part(folder, 'date.html', re.sub(r'<time>.*?</time>', '<time>%s</time>' % he_date(date), read_part(newest_dir, 'date.html'), count=1))
    write_part(folder, 'image.html', image_part(sizes, alt))
    write_part(folder, 'content.html', '\n\t\t\t\t\t' + content + '\n\t\t\t\t')
    write_part(folder, 'navigation.html', navigation(read_part(newest_dir, 'navigation.html'), newest, None))
    write_part(folder, 'comments.html', comments_part(read_part(newest_dir, 'comments.html'), newest['url'], url, new_id))
    write_page_json(folder, {'output': urllib.parse.unquote(url).strip('/') + '/index.html', 'layout': POST_LAYOUT,
                             'params': post_params(old['params'], new_id, url, title, sizes)})

def cmd_add(spec_file):
    spec = json.load(open(spec_file, encoding='utf-8'))
    posts = json.load(open(DATA, encoding='utf-8'))
    slug = spec['slug'].strip('/')
    url = '/' + urllib.parse.quote(slug) + '/'
    if any(p['url'] == url for p in posts):
        sys.exit('a post with this address already exists: ' + url)
    folder = post_folder(url)
    if os.path.exists(folder):
        sys.exit('this post already has a folder in src: ' + folder)
    date = datetime.date.fromisoformat(spec.get('date') or datetime.date.today().isoformat())
    title = spec['title'].strip()
    alt = spec.get('image_alt') or title
    content = spec['content_html']
    plain = re.sub(r'https?://\S+', '', text_of(content))
    description = spec.get('description') or words(plain, 30)
    new_id = max(p['id'] for p in posts) + 1
    newest = posts[0]
    newest_dir = post_folder(newest['url'])
    if not os.path.exists(os.path.join(newest_dir, 'page.json')):
        sys.exit('the newest post has no folder in src: ' + newest_dir)
    sizes = save_images(spec['image'], slug, date)

    seo = seo_part(read_part(newest_dir, 'seo.html'), url, title, description, alt, sizes)
    write_new_post(folder, newest_dir, newest, url, title, date, content, seo, alt, sizes, new_id)
    # the post before it now gets a "next" link
    write_part(newest_dir, 'navigation.html', navigation(read_part(newest_dir, 'navigation.html'),
                                                         posts[1] if len(posts) > 1 else None, {'url': url, 'title': title}))
    posts.insert(0, post_entry(new_id, url, title, plain, alt, sizes,
                               spec.get('author') or newest.get('author') or 'יוחי דנחי', date))
    json.dump(posts, open(DATA, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)
    cmd_lists()
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'sitemap.py'), ROOT], check=True)
    print('added', url)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'index':
        cmd_index()
    elif cmd == 'lists':
        cmd_lists()
    elif cmd == 'add':
        cmd_add(sys.argv[2])
    else:
        sys.exit(__doc__)
