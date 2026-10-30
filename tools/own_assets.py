#!/usr/bin/env python3
"""Make the static site independent of the WordPress folders on the server.

The copy of WordPress's files that the static site uses (images, styles, scripts,
fonts) sits in site/wp-content and site/wp-includes. On the server those two
addresses are answered by WordPress itself, so a WordPress cache clear, plugin
update, deleted image or the removal of WordPress would break the static pages.

This tool moves them to the static site's own folder:
    wp-content/<x>   -> assets/wp/<x>
    wp-includes/<x>  -> assets/wp-includes/<x>
and points every reference at the new place: page attributes, inline styles and
scripts (also the escaped \\/wp-content\\/ form inside script settings), Elementor
lightbox links (whose settings are base64 inside the link), styles, scripts,
sitemaps and data/posts.json. Full addresses keep their https://www.victory.org.il
start (sharing previews need it); all others become root-relative.

Safe to run more than once. Usage: python3 tools/own_assets.py site [data/posts.json]
"""
import base64
import os
import re
import shutil
import sys
from urllib.parse import quote, unquote

ROOT = sys.argv[1] if len(sys.argv) > 1 else 'site'
EXTRA = sys.argv[2:]  # other text files to update, e.g. data/posts.json
MOVES = (('wp-content', 'assets/wp'), ('wp-includes', 'assets/wp-includes'))
NEW = dict(MOVES)
TEXT_EXT = ('.html', '.css', '.js', '.json', '.xml', '.txt', '.svg')

HOST = r'(?:https?:)?//(?:www\.)?victory\.org\.il/'
PLAIN = re.compile(r'(?<![\w.%/\\-])(' + HOST + r'|/|(?:\.\./)+|\./)?(wp-content|wp-includes)/')
ESC_HOST = r'(?:https?:)?\\/\\/(?:www\.)?victory\.org\.il\\/'
ESCAPED = re.compile(r'(?<![\w.%/\\-])(' + ESC_HOST + r'|\\/)(wp-content|wp-includes)\\/')
LIGHTBOX = re.compile(r'(elementor-action%3Aaction%3Dlightbox%26settings%3D)([A-Za-z0-9%+/=]+)')


def rewrite(text):
    def plain(m):
        prefix, folder = m.group(1) or '', m.group(2)
        start = prefix if re.match(HOST, prefix) else '/'
        return start + NEW[folder] + '/'

    def escaped(m):
        prefix, folder = m.group(1), m.group(2)
        start = prefix if prefix != '\\/' else '\\/'
        return start + NEW[folder].replace('/', '\\/') + '\\/'

    def lightbox(m):
        raw = unquote(m.group(2))
        try:
            data = base64.b64decode(raw + '=' * (-len(raw) % 4)).decode('utf-8')
        except Exception:
            return m.group(0)
        new = ESCAPED.sub(escaped, PLAIN.sub(plain, data))
        if new == data:
            return m.group(0)
        return m.group(1) + quote(base64.b64encode(new.encode('utf-8')).decode('ascii'), safe='')

    text = LIGHTBOX.sub(lightbox, text)
    text = ESCAPED.sub(escaped, text)
    return PLAIN.sub(plain, text)


def move_folders():
    moved = 0
    for old, new in MOVES:
        src_root = os.path.join(ROOT, old)
        if not os.path.isdir(src_root):
            continue
        for dirpath, _, files in os.walk(src_root):
            for name in files:
                src = os.path.join(dirpath, name)
                dst = os.path.join(ROOT, new, os.path.relpath(src, src_root))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if os.path.exists(dst):
                    os.remove(dst)
                shutil.move(src, dst)
                moved += 1
        shutil.rmtree(src_root)
    return moved


def update_text(paths):
    changed = 0
    for path in paths:
        with open(path, encoding='utf-8', errors='surrogateescape') as f:
            text = f.read()
        new = rewrite(text)
        if new != text:
            with open(path, 'w', encoding='utf-8', errors='surrogateescape') as f:
                f.write(new)
            changed += 1
    return changed


def text_files():
    for dirpath, _, files in os.walk(ROOT):
        for name in files:
            if name.endswith(TEXT_EXT):
                yield os.path.join(dirpath, name)


if __name__ == '__main__':
    print('files moved:', move_folders())
    print('files updated:', update_text(list(text_files()) + [p for p in EXTRA if os.path.isfile(p)]))
