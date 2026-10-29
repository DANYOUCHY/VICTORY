"""Turn the raw WordPress copy in site/ into a clean static site.

1. maps WordPress short links (?p=123) to the real page address
2. renames files saved with query strings (style.css?ver=1.2.css -> style.css)
3. fixes every reference to match
4. points absolute www.victory.org.il links to the local copy (root-relative),
   keeping canonical / og tags absolute for search engines and sharing
5. removes WordPress-only head tags (REST API, XML-RPC, feeds, oEmbed, short links)
6. removes comment forms, which need WordPress to work
7. deletes the duplicate short-link pages
Safe to run more than once.
"""
import glob
import os
import re
import sys
from urllib.parse import unquote, urlparse

root = sys.argv[1] if len(sys.argv) > 1 else 'site'

def files(exts):
    for f in glob.glob(os.path.join(root, '**', '*'), recursive=True):
        if os.path.isfile(f) and f.endswith(exts):
            yield f

# 1. short-link map: post id -> /path/
pmap = {}
for f in [x for x in glob.glob(os.path.join(root, '*')) if '?p=' in x]:
    m = re.search(r'\?p=(\d+)', f)
    t = open(f, encoding='utf-8', errors='ignore').read()
    c = re.search(r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+)', t)
    if m and c:
        pmap[m.group(1)] = urlparse(c.group(1)).path or '/'
print('short links mapped:', len(pmap))

# 2. rename files whose names carry a query string
renamed = 0
for f in sorted((x for x in glob.glob(os.path.join(root, '**', '*'), recursive=True) if '?' in os.path.basename(x)), key=len, reverse=True):
    if '?p=' in os.path.basename(f) or not os.path.isfile(f):
        continue
    base = os.path.basename(f).split('?')[0]
    new = os.path.join(os.path.dirname(f), base)
    if os.path.exists(new):
        os.remove(f)
    else:
        os.rename(f, new)
    renamed += 1
print('files renamed:', renamed)

HEAD_JUNK = re.compile(
    r'<link[^>]+(?:'
    r'rel=["\'](?:EditURI|pingback|shortlink|wlwmanifest|alternate)["\'][^>]*(?:json|xml|feed|oembed)'
    r'|rel=["\'](?:EditURI|pingback|shortlink|wlwmanifest)["\']'
    r'|href=["\'][^"\']*(?:wp-json|xmlrpc\.php|/feed/|oembed)[^"\']*["\']'
    r'|rel=["\']https://api\.w\.org/["\']'
    r')[^>]*/?>\s*',
    re.I)
ABS = re.compile(r'(?<=["\'(\s,=])(?:https?:)?(\\?/)\1(?:www\.)?victory\.org\.il(?=\\?/|["\'])')
COMMENT_FORM = re.compile(r'<div id="respond".*?</form>\s*</div>', re.S)
# local file reference followed by a query string, as plain "?" or saved as "%3F"
LOCAL_QUERY = re.compile(
    r'(?<![\w.:/-])((?:/|\.\./|\./|wp-content/|wp-includes/)[^"\'\s()<>]*?'
    r'\.(?:css|js|png|jpe?g|webp|gif|svg|ico|woff2?|ttf|eot|otf|html))'
    r'(?:%3F|\?)[^"\'\s()<>`;{}]*', re.I)
SHORT = re.compile(r'(?:(?:\.\./)*|/)?index\.html%3Fp=(\d+)\.html|(?<=["\'])/?\?p=(\d+)')

def short(m):
    pid = m.group(1) or m.group(2)
    return pmap.get(pid, m.group(0))

changed = 0
for f in files(('.html', '.css', '.js')):
    if '?p=' in f:
        continue
    t = open(f, encoding='utf-8', errors='ignore').read()
    o = t
    keep = {}
    def stash(m):
        keep[len(keep)] = m.group(0)
        return '\0%d\0' % (len(keep) - 1)
    if f.endswith('.html'):
        t = HEAD_JUNK.sub('', t)
        # wget made canonical links relative; point them back at the real address
        og = re.search(r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\'](https?://[^"\']+)', t)
        if og:
            t = re.sub(r'<link rel="canonical" href="[^"]*"', '<link rel="canonical" href="%s"' % og.group(1), t)
        t = COMMENT_FORM.sub('', t)
        # Elementor buttons (popups, lightboxes) need a bare #elementor-action link
        t = re.sub(r'href="[^"#]*(#elementor-action)', r'href="\1', t)
        t = re.sub(r'<(?:link[^>]+rel=["\']canonical["\']|meta[^>]+(?:og:url|og:image|twitter:image))[^>]*>', stash, t)
        t = re.sub(r'<script type="application/ld\+json".*?</script>', stash, t, flags=re.S)
    t = ABS.sub('', t)
    if not f.endswith('.js'):  # scripts build URLs in code; leave them alone
        t = SHORT.sub(short, t)
        t = LOCAL_QUERY.sub(lambda m: m.group(1), t)
    t = re.sub(r'\0(\d+)\0', lambda m: keep[int(m.group(1))], t)
    if t != o:
        open(f, 'w', encoding='utf-8').write(t)
        changed += 1
print('files changed:', changed)

# 7. duplicate short-link pages
for f in [x for x in glob.glob(os.path.join(root, '*')) if '?p=' in x]:
    os.remove(f)
