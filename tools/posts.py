"""Manage blog posts on the static site.

  python3 tools/posts.py index              build data/posts.json from the site as it is now
  python3 tools/posts.py add post.json      add a new post (see NEW POST below)
  python3 tools/posts.py lists              rebuild the blog pages and the "recent posts"
                                            sidebar on every page from data/posts.json

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

A new post is built from the newest existing post page, so it has exactly the same
layout. Adding a post also updates the previous post's "next" link, every blog page,
the recent-posts sidebar on every page and the sitemaps.
"""
import datetime
import glob
import html
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse

ROOT = 'site'
DATA = 'data/posts.json'
BASE = 'https://www.victory.org.il'
PER_PAGE = 8
SIDEBAR_COUNT = 3
BLOG_WORDS, SIDEBAR_WORDS = 25, 20
MONTHS_HE = ['ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני', 'יולי', 'אוגוסט',
             'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר']


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
    return re.sub(r'(?:\.\./)+(wp-content|wp-includes)/', r'/\1/', s)

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


# ---------- list rendering ----------

def para(s):
    return '<p>%s</p>' % html.escape(s, quote=False) if s else ''

ARTICLE_CLASS = ('elementor-post elementor-grid-item post-%d post type-post status-publish '
                 'format-standard has-post-thumbnail hentry category-uncategorized')

def blog_article(p, first):
    thumb = p['thumb']
    if not first:
        thumb = thumb.replace('fetchpriority="high" ', '')
    thumb_link = ('\t\t\t\t<a class="elementor-post__thumbnail__link" href="%s" tabindex="-1" >\n'
                  '\t\t\t<div class="elementor-post__thumbnail">%s</div>\n\t\t</a>\n' % (p['url'], thumb)) if thumb else ''
    return (
        '<article class="%s" role="listitem">\n'
        '%s'
        '\t\t\t\t<div class="elementor-post__text">\n'
        '\t\t\t\t<h3 class="elementor-post__title">\n\t\t\t<a href="%s" >\n\t\t\t\t%s\t\t\t</a>\n\t\t</h3>\n'
        '\t\t\t\t<div class="elementor-post__meta-data">\n\t\t\t\t\t<span class="elementor-post-author">\n'
        '\t\t\t%s\t\t</span>\n\t\t\t\t</div>\n'
        '\t\t\t\t<div class="elementor-post__excerpt">\n\t\t\t%s\n\t\t</div>\n'
        '\t\t\n\t\t<a class="elementor-post__read-more" href="%s" aria-label="קרא עוד אודות %s" tabindex="-1" >\n'
        '\t\t\tקראו עוד »\t\t</a>\n\n\t\t\t\t</div>\n\t\t\t\t</article>\n'
    ) % (p.get('cls') or ARTICLE_CLASS % p['id'], thumb_link, p['url'], html.escape(p['title'], quote=False),
         html.escape(p['author'] or 'יוחי דנחי', quote=False), p.get('excerpt_html', para(p['excerpt'])),
         p['url'], attr(p['title']))

def sidebar_article(p):
    return (
        '<article class="%s" role="listitem">\n'
        '\t\t\t\t<div class="elementor-post__text">\n'
        '\t\t\t\t<h3 class="elementor-post__title">\n\t\t\t<a href="%s" >\n\t\t\t\t%s\t\t\t</a>\n\t\t</h3>\n'
        '\t\t\t\t<div class="elementor-post__excerpt">\n\t\t\t%s\n\t\t</div>\n'
        '\t\t\n\t\t<a class="elementor-post__read-more" href="%s" aria-label="קרא עוד אודות %s" tabindex="-1" >\n'
        '\t\t\tקראו עוד...\t\t</a>\n\n\t\t\t\t</div>\n\t\t\t\t</article>\n'
    ) % (p.get('cls') or ARTICLE_CLASS % p['id'], p['url'], html.escape(p['title'], quote=False),
         p.get('excerpt_short_html', ''), p['url'], attr(p['title']))

def pagination(page, last):
    def link(n):
        return '/blog/' if n == 1 else '/blog/%d/' % n
    parts = []
    parts.append('<a class="page-numbers prev" href="%s">&laquo; הקודם</a>' % link(page - 1) if page > 1
                 else '<span class="page-numbers prev">&laquo; הקודם</span>')
    for n in range(1, last + 1):
        if n == page:
            parts.append('<span aria-current="page" class="page-numbers current"><span class="elementor-screen-only">עמוד</span>%d</span>' % n)
        else:
            parts.append('<a class="page-numbers" href="%s"><span class="elementor-screen-only">עמוד</span>%d</a>' % (link(n), n))
    parts.append('<a class="page-numbers next" href="%s">הבא &raquo;</a>' % link(page + 1) if page < last
                 else '<span class="page-numbers next">הבא &raquo;</span>')
    return ('\t\t<div class="e-load-more-anchor" data-page="%d" data-max-page="%d" data-next-page="%s"></div>\n'
            '\t\t\t\t<nav class="elementor-pagination" aria-label="עימוד">\n\t\t\t%s\t\t</nav>\n'
            ) % (page, last, BASE + link(min(page + 1, last)), ' \n'.join(parts))

def cmd_lists():
    posts = json.load(open(DATA, encoding='utf-8'))
    pages = [posts[i:i + PER_PAGE] for i in range(0, len(posts), PER_PAGE)]
    for n, chunk in enumerate(pages, 1):
        f = os.path.join(ROOT, 'blog', 'index.html') if n == 1 else os.path.join(ROOT, 'blog', str(n), 'index.html')
        t = open(f, encoding='utf-8').read() if os.path.exists(f) else ''
        if 'data-widget_type="posts.classic"' not in t:
            # a new last page (or WordPress's empty one): copy page 2 and give it this page's address
            t = open(os.path.join(ROOT, 'blog', '2', 'index.html'), encoding='utf-8').read()
            t = t.replace(BASE + '/blog/2/"', BASE + '/blog/%d/"' % n)
            os.makedirs(os.path.dirname(f), exist_ok=True)
        span = widget_spans(t, 'posts.classic')[0]
        inner = ('\n\t\t\t<div class="elementor-posts-container elementor-posts elementor-posts--skin-classic elementor-grid" role="list">\n'
                 + ''.join(blog_article(p, i == next((k for k, q in enumerate(chunk) if q['thumb']), -1))
                           for i, p in enumerate(chunk))
                 + '\t\t\t\t</div>\n' + pagination(n, len(pages)) + '\t\t\t\t')
        t = replace_widget_inner(t, span, inner)
        open(f, 'w', encoding='utf-8').write(t)
    def side_for(own_id):
        shown = [p for p in posts if p['id'] != own_id][:SIDEBAR_COUNT]
        return ('\n\t\t\t<div class="elementor-posts-container elementor-posts elementor-posts--skin-classic elementor-grid" role="list">\n'
                + ''.join(sidebar_article(p) for p in shown) + '\t\t\t\t</div>\n\t\t\t\t')
    changed = 0
    for f in glob.glob(os.path.join(ROOT, '**', '*.html'), recursive=True):
        if os.sep + 'blog' + os.sep in f or f.startswith(os.path.join(ROOT, 'wp-')):
            continue
        t = open(f, encoding='utf-8').read()
        o = t
        own = re.search(r'\bpostid-(\d+)\b', t)
        side = side_for(int(own.group(1)) if own else None)
        for span in reversed(widget_spans(t, 'posts.classic')):
            if 'elementor-posts--thumbnail-none' in t[span[0]:t.find('>', span[0])]:
                t = replace_widget_inner(t, span, side)
        if t != o:
            open(f, 'w', encoding='utf-8').write(t)
            changed += 1
    print('blog pages:', len(pages), '| pages with recent posts updated:', changed)


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

def copy_nav_arrows(t, span):
    """Keep the arrow icons the site already uses (svg or font icon) when rebuilding the navigation."""
    seg = t[span[0]:span[1]]
    prev_icon = re.search(r'post-navigation__arrow-prev">(.*?)<span class="elementor-screen-only">', seg, re.S)
    next_icon = re.search(r'post-navigation__arrow-next">(.*?)<span class="elementor-screen-only">', seg, re.S)
    return (prev_icon.group(1) if prev_icon else '', next_icon.group(1) if next_icon else '')

def set_nav(t, prev_p, next_p):
    span = widget_spans(t, 'post-navigation.default')[0]
    pi, ni = copy_nav_arrows(t, span)
    inner = nav_inner(prev_p, next_p)
    inner = inner.replace('<i aria-hidden="true" class="fa fa-angle-right"></i>', pi or '')
    inner = inner.replace('<i aria-hidden="true" class="fa fa-angle-left"></i>', ni or '')
    return replace_widget_inner(t, span, inner)

def save_images(src, slug, date):
    from PIL import Image
    im = Image.open(src).convert('RGB')
    w, h = im.size
    folder = os.path.join(ROOT, 'wp-content', 'uploads', '%04d' % date.year, '%02d' % date.month)
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

def cmd_add(spec_file):
    spec = json.load(open(spec_file, encoding='utf-8'))
    posts = json.load(open(DATA, encoding='utf-8'))
    slug = spec['slug'].strip('/')
    url = '/' + urllib.parse.quote(slug) + '/'
    if any(p['url'] == url for p in posts):
        sys.exit('a post with this address already exists: ' + url)
    date = datetime.date.fromisoformat(spec.get('date') or datetime.date.today().isoformat())
    title = spec['title'].strip()
    alt = spec.get('image_alt') or title
    content = spec['content_html']
    plain = re.sub(r'https?://\S+', '', text_of(content))
    excerpt = words(plain, BLOG_WORDS)
    description = spec.get('description') or words(plain, 30)
    new_id = max(p['id'] for p in posts) + 1
    sizes = save_images(spec['image'], slug, date)

    newest = posts[0]
    t = open(page_file(newest['url']), encoding='utf-8').read()
    old_id = newest['id']

    # head
    t = re.sub(r'<title>.*?</title>', '<title>%s</title>' % html.escape(title, quote=False), t, count=1, flags=re.S)
    def meta(t, key, value, prop=True):
        k = 'property' if prop else 'name'
        return re.sub(r'(<meta %s="%s" content=")[^"]*(")' % (k, re.escape(key)), lambda m: m.group(1) + attr(value) + m.group(2), t)
    t = meta(t, 'description', description, prop=False)
    for k, v in (('og:url', BASE + url), ('og:title', title), ('og:description', description),
                 ('og:image', BASE + sizes['og'][0]), ('og:image:secure_url', BASE + sizes['og'][0]),
                 ('og:image:width', str(sizes['og'][1][0])), ('og:image:height', str(sizes['og'][1][1])),
                 ('og:image:alt', alt)):
        t = meta(t, k, v)
    for k, v in (('twitter:title', title), ('twitter:description', description), ('twitter:image', BASE + sizes['og'][0])):
        t = meta(t, k, v, prop=False)
    t = re.sub(r'<link rel="canonical" href="[^"]*"', '<link rel="canonical" href="%s"' % (BASE + url), t)

    # ids and the page settings Elementor reads (share buttons use the title and image)
    t = t.replace('postid-%d' % old_id, 'postid-%d' % new_id).replace('post-%d ' % old_id, 'post-%d ' % new_id)
    t = re.sub(r'"post":\{"id":%d,"title":"[^"]*","excerpt":"[^"]*","featuredImage":"[^"]*"' % old_id,
               lambda m: '"post":{"id":%d,"title":"%s","excerpt":"","featuredImage":"%s"}'[:-1] % (
                   new_id, urllib.parse.quote(title), (BASE + sizes['large'][0]).replace('/', '\\/')), t)

    # body widgets
    span = widget_spans(t, 'theme-post-title.default')[0]
    t = t[:span[0]] + re.sub(r'(<h1[^>]*>).*?(</h1>)', lambda m: m.group(1) + html.escape(title, quote=False) + m.group(2),
                             t[span[0]:span[1]], count=1, flags=re.S) + t[span[1]:]
    span = widget_spans(t, 'post-info.default')[0]
    t = t[:span[0]] + re.sub(r'<time>.*?</time>', '<time>%s</time>' % he_date(date), t[span[0]:span[1]], count=1) + t[span[1]:]
    span = widget_spans(t, 'theme-post-featured-image.default')[0]
    ml = sizes['medium_large']
    img = ('<img fetchpriority="high" width="%d" height="%d" src="%s" class="attachment-medium_large size-medium_large" '
           'alt="%s" srcset="%s" sizes="(max-width: %dpx) 100vw, %dpx" />') % (ml[1][0], ml[1][1], ml[0], attr(alt), srcset(sizes), ml[1][0], ml[1][0])
    t = replace_widget_inner(t, span, '\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t' + img + '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t')
    span = widget_spans(t, 'theme-post-content.default')[0]
    t = replace_widget_inner(t, span, '\n\t\t\t\t\t' + content + '\n\t\t\t\t')
    t = set_nav(t, newest, None)
    # comments: a new post starts with none
    span = widget_spans(t, 'post-comments.theme_comments')[0]
    seg = t[span[0]:span[1]]
    seg = re.sub(r'<h3 class="comments-title">.*?</h3>', '', seg, flags=re.S)
    seg = re.sub(r'<ol class="ast-comment-list">.*?</ol>|<ol class="comment-list">.*?</ol>', '', seg, flags=re.S)
    seg = re.sub(r"(name=['\"]comment_post_ID['\"] value=['\"])\d+", lambda m: m.group(1) + str(new_id), seg)
    seg = seg.replace(newest['url'] + '#respond', url + '#respond')
    t = t[:span[0]] + seg + t[span[1]:]

    out = page_file(url)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', encoding='utf-8').write(t)

    # previous newest post now gets a "next" link
    pf = page_file(newest['url'])
    pt = open(pf, encoding='utf-8').read()
    prev_of_newest = posts[1] if len(posts) > 1 else None
    open(pf, 'w', encoding='utf-8').write(set_nav(pt, prev_of_newest, {'url': url, 'title': title}))

    medium = sizes['medium']
    thumb = ('<img fetchpriority="high" decoding="async" width="%d" height="%d" src="%s" class="attachment-medium size-medium" '
             'alt="%s" srcset="%s" sizes="(max-width: %dpx) 100vw, %dpx" />') % (
        medium[1][0], medium[1][1], medium[0], attr(alt), srcset(sizes), medium[1][0], medium[1][0])
    posts.insert(0, {'id': new_id, 'url': url, 'title': title, 'excerpt': excerpt,
                     'excerpt_html': para(excerpt), 'excerpt_short_html': para(words(plain, SIDEBAR_WORDS)),
                     'cls': ARTICLE_CLASS % new_id, 'thumb': thumb,
                     'author': spec.get('author') or newest.get('author') or 'יוחי דנחי',
                     'date': date.isoformat()})
    json.dump(posts, open(DATA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
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
