#!/usr/bin/env python3
"""Audit: does the static site still depend on WordPress?

Lists, for every page, style and script in site/:
  - local files it refers to that are missing from site/
  - addresses that only WordPress can answer (wp-json, admin-ajax, xmlrpc, wp-login,
    wp-admin, ?p= short links, feeds, search)
  - references to WordPress folders (/wp-content/, /wp-includes/), which the server
    serves from WordPress itself rather than from the static copy
Usage: python3 tools/audit_wp.py site [--json out.json]
"""
import json
import os
import re
import sys
from collections import defaultdict
from urllib.parse import unquote, urljoin, urlparse

ROOT = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else 'site'
OUT = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
HOSTS = {'www.victory.org.il', 'victory.org.il'}

ATTR_RE = re.compile(r'''\b(href|src|srcset|data-src|data-srcset|data-lazy-src|data-bg|poster|action|data-thumbnail|content|data-url|data-href)\s*=\s*(["'])(.*?)\2''', re.I | re.S)
CSS_URL_RE = re.compile(r'''url\(\s*(["']?)([^"')]+)\1\s*\)''')
DYN_RE = re.compile(r'(wp-json|admin-ajax\.php|xmlrpc\.php|wp-login\.php|/wp-admin|wp-cron\.php|[?&](?:p|page_id|s|replytocom)=|/feed/?(?:["\'?#]|$)|/comments/feed|/trackback)', re.I)
WPDIR_RE = re.compile(r'^/(wp-content|wp-includes)/')
A11Y = ('grayscale', 'high-contrast', 'light-background', 'links-underline', 'negative-contrast',
        'readable-font', 'reset', 'resize-minus', 'resize-plus')  # accessibility toolbar actions, not files
JS_STR_RE = re.compile(r'''(["'])((?:https?:)?(?:\\?/\\?/)?(?:www\.)?victory\.org\.il[^"'\s<>]*|[^"'\s<>]*(?:wp-content|wp-includes|wp-json|admin-ajax|xmlrpc)[^"'\s<>]*)\1''')

missing = defaultdict(set)      # local path -> pages
dynamic = defaultdict(set)      # url -> pages
wpdir_refs = defaultdict(int)   # top folder -> count
pages = 0


def norm_local(ref, base_url):
    ref = ref.strip().replace('\\/', '/').replace('&amp;', '&')
    if not ref or ref.startswith(('data:', 'mailto:', 'tel:', 'javascript:', '#', 'about:', 'blob:', '{{', '<')):
        return None
    u = urlparse(urljoin(base_url, ref))
    if u.scheme not in ('http', 'https') or u.netloc not in HOSTS:
        return None
    return u


def exists(path):
    p = unquote(path)
    f = os.path.join(ROOT, p.lstrip('/'))
    if p.endswith('/'):
        return os.path.isfile(os.path.join(f, 'index.html'))
    if os.path.isfile(f):
        return True
    return os.path.isfile(os.path.join(f, 'index.html'))


def check(ref, base_url, where, kind):
    u = norm_local(ref, base_url)
    if not u:
        return
    full = u.path + ('?' + u.query if u.query else '')
    if DYN_RE.search(full):
        dynamic[full].add(where)
        return
    m = WPDIR_RE.search(u.path)
    if m:
        wpdir_refs[m.group(1)] += 1
    if not exists(u.path) and not u.path.rstrip('/').endswith(A11Y):
        missing[unquote(u.path)].add(where)


for dirpath, _, files in os.walk(ROOT):
    for name in files:
        path = os.path.join(dirpath, name)
        rel = os.path.relpath(path, ROOT).replace(os.sep, '/')
        base_url = 'https://www.victory.org.il/' + rel
        if name.endswith('.html'):
            pages += 1
            text = open(path, encoding='utf-8', errors='ignore').read()
            text = re.sub(r'<!--(?!\[if).*?-->', '', text, flags=re.S)   # commented-out tags load nothing
            for attr, _, val in ATTR_RE.findall(text):
                if attr.lower() == 'content' and not re.match(r'(https?:)?//|/', val.strip()):
                    continue
                vals = [v.strip().split(' ')[0] for v in val.split(',')] if 'srcset' in attr.lower() else [val]
                for v in vals:
                    check(v, base_url, rel, attr)
            for _, v in CSS_URL_RE.findall(text):
                check(v, base_url, rel, 'style')
            for script in re.findall(r'<script\b[^>]*>(.*?)</script>', text, re.S | re.I):
                for _, v in JS_STR_RE.findall(script):
                    check(v, base_url, rel, 'script')
        elif name.endswith('.css'):
            text = open(path, encoding='utf-8', errors='ignore').read()
            for _, v in CSS_URL_RE.findall(text):
                check(v, base_url, rel, 'css')
            for v in re.findall(r'@import\s+["\']([^"\']+)', text):
                check(v, base_url, rel, 'css')

report = {
    'pages': pages,
    'wp_folder_refs': dict(wpdir_refs),
    'missing_files': {k: sorted(v)[:3] + (['… +%d' % (len(v) - 3)] if len(v) > 3 else []) for k, v in sorted(missing.items())},
    'wordpress_only_addresses': {k: sorted(v)[:3] + (['… +%d' % (len(v) - 3)] if len(v) > 3 else []) for k, v in sorted(dynamic.items())},
}
if OUT:
    json.dump(report, open(OUT, 'w'), ensure_ascii=False, indent=1)
print('pages:', pages)
print('references into WordPress folders (/wp-content/, /wp-includes/):', dict(wpdir_refs) or 0)
print('missing local files:', len(missing))
for k, v in sorted(missing.items())[:80]:
    print('  MISSING', k, '<-', len(v), 'file(s), e.g.', sorted(v)[0])
print('WordPress-only addresses:', len(dynamic))
for k, v in sorted(dynamic.items())[:80]:
    print('  DYNAMIC', k[:140], '<-', len(v), 'file(s), e.g.', sorted(v)[0])
