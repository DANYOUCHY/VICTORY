"""Write the sitemaps and robots.txt for the static site, in the same layout as
WordPress/SEOPress had them: /sitemaps.xml points to post-sitemap1.xml and
page-sitemap1.xml. Run after any page or post is added or changed.

Usage: python3 tools/sitemap.py site
"""
import glob
import os
import re
import sys
import urllib.parse
from datetime import datetime, timezone

root = sys.argv[1] if len(sys.argv) > 1 else 'site'
BASE = 'https://www.victory.org.il'

MONTHS = {'ינואר': 1, 'פברואר': 2, 'מרץ': 3, 'מרס': 3, 'אפריל': 4, 'מאי': 5, 'יוני': 6, 'יולי': 7,
          'אוגוסט': 8, 'ספטמבר': 9, 'אוקטובר': 10, 'נובמבר': 11, 'דצמבר': 12}

def post_date(t):
    """The date shown on the post (e.g. 'אוקטובר 23, 2026'), or None for pages."""
    m = re.search(r'<time[^>]*>\s*(\S+) (\d{1,2}), (\d{4})', t)
    if m and m.group(1) in MONTHS:
        return '%s-%02d-%02d' % (m.group(3), MONTHS[m.group(1)], int(m.group(2)))
    return None

posts, pages = [], []
for f in sorted(glob.glob(os.path.join(root, '**', 'index.html'), recursive=True)):
    rel = os.path.relpath(os.path.dirname(f), root)
    if rel.startswith(('wp-', 'thanks', 'blog/')) or re.match(r'^blog/\d+$', rel):
        continue
    t = open(f, encoding='utf-8', errors='ignore').read()
    if re.search(r'<meta name=["\']robots["\'][^>]*noindex', t):
        continue
    path = '/' if rel == '.' else '/' + urllib.parse.quote(rel) + '/'
    lastmod = post_date(t)
    body = re.search(r'<body[^>]*class=["\']([^"\']*)', t)
    is_post = bool(body and 'single-post' in body.group(1).split())
    (posts if is_post else pages).append((BASE + path, lastmod))

def urlset(items):
    rows = ''.join('<url>\n<loc>%s</loc>\n%s</url>\n' % (u, '<lastmod>%s</lastmod>\n' % d if d else '')
                   for u, d in items)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s</urlset>\n' % rows)

def newest(items):
    return max((d for _, d in items if d), default=datetime.now(timezone.utc).strftime('%Y-%m-%d'))

open(os.path.join(root, 'post-sitemap1.xml'), 'w', encoding='utf-8').write(urlset(posts))
open(os.path.join(root, 'page-sitemap1.xml'), 'w', encoding='utf-8').write(urlset(pages))
index = ('<?xml version="1.0" encoding="UTF-8"?>\n'
         '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
         '<sitemap>\n<loc>%s/post-sitemap1.xml</loc>\n<lastmod>%s</lastmod>\n</sitemap>\n'
         '<sitemap>\n<loc>%s/page-sitemap1.xml</loc>\n<lastmod>%s</lastmod>\n</sitemap>\n'
         '</sitemapindex>\n') % (BASE, newest(posts), BASE, newest(pages))
open(os.path.join(root, 'sitemaps.xml'), 'w', encoding='utf-8').write(index)
open(os.path.join(root, 'robots.txt'), 'w', encoding='utf-8').write(
    'User-agent: *\nDisallow: /wp-admin/\n\nSitemap: %s/sitemaps.xml\n' % BASE)
print('posts:', len(posts), '| pages:', len(pages))
