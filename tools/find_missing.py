"""List victory.org.il URLs referenced by files in site/ that are not saved locally yet."""
import re, os, sys, glob, urllib.parse
root = sys.argv[1] if len(sys.argv) > 1 else 'site'
pat = re.compile(r'(?:https?:)?(?<![\w/])(?:\\?/){2}(?:www\.)?victory\.org\.il((?:\\?/)[^\s"\'()<>,]*)')
skip = re.compile(r'(wp-json|xmlrpc|/feed/?|comments-post|\?p=|wp-admin|wp-login|/embed/?$|oembed|admin-ajax)')
need = set()
for f in glob.glob(os.path.join(root, '**', '*'), recursive=True):
    if not f.endswith(('.html', '.css', '.js')) or '?p=' in f:
        continue
    t = open(f, encoding='utf-8', errors='ignore').read()
    for m in pat.finditer(t):
        p = m.group(1).split('&quot;')[0].replace('\\/', '/').replace('&#038;', '&').replace('&amp;', '&').rstrip('\\')
        p = p.split('#')[0].split('?')[0]
        if not p or skip.search(p):
            continue
        local = os.path.join(root, urllib.parse.unquote(p).lstrip('/'))
        if p.endswith('/'):
            local = os.path.join(local, 'index.html')
        if not (os.path.exists(local) or os.path.exists(local + '.html')):
            need.add(p)
for n in sorted(need):
    print('https://www.victory.org.il' + n)
