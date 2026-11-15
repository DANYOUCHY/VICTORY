"""Remove "index.html" from links inside the site's pages.

A link like href="../index.html" or href="index.html#contact" makes browsers and search
engines ask for an address that ends in index.html. That address shows the same page as the
clean one (/ or /blog/), so search engines see the page twice. The server now answers such
addresses with a 301 (site/.htaccess), and this tool keeps the pages from linking there at all.

  python tools/clean_index_links.py [folder]     (default: site)

Only relative links are changed: "index.html" -> "./", "index.html#x" -> "#x",
"../index.html" -> "../", "blog/2/index.html" -> "blog/2/". Files keep their line endings (LF).
"""
import glob
import os
import re
import sys

root = sys.argv[1] if len(sys.argv) > 1 else 'site'
LINK = re.compile(r'((?:href|action)=")((?:\.\./|[^"#?:]*/)*)index\.html([#?][^"]*)?"')


def fix(m):
    attr, path, rest = m.group(1), m.group(2), m.group(3) or ''
    if path:
        return f'{attr}{path}{rest}"'
    if rest.startswith('#'):
        return f'{attr}{rest}"'
    return f'{attr}./{rest}"'


changed = 0
for f in glob.glob(os.path.join(root, '**', '*.html'), recursive=True):
    with open(f, 'rb') as fh:
        raw = fh.read()
    text = raw.decode('utf-8')
    new = LINK.sub(fix, text)
    if new != text:
        with open(f, 'wb') as fh:
            fh.write(new.encode('utf-8'))
        changed += 1
print(f'index.html links cleaned in {changed} files')
