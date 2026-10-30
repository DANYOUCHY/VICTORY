#!/usr/bin/env python3
"""Keep the page styles that WordPress generates inside the static site.

Elementor page styles (wp-content/uploads/elementor/css/) and WP Fastest Cache
combined styles (wp-content/cache/wpfc-minified/) are cache files: WordPress
deletes them whenever its cache is cleared or a plugin updates. On the server,
/wp-content/ is always served from WordPress, so when that happened the static
pages lost their design.

This moves those files to /assets/wp/ inside the static site, points every page
at the new place, and turns relative addresses inside the styles (fonts, icons)
into full /wp-content/ addresses so they still load.

Usage: python3 tools/own_css.py site
"""
import os
import posixpath
import re
import shutil
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "site"
FOLDERS = ("wp-content/cache/wpfc-minified/", "wp-content/uploads/elementor/css/")
NEW_BASE = "assets/wp/"  # wp-content/<x> -> assets/wp/<x>

URL_RE = re.compile(r"url\(\s*(['\"]?)([^'\")]+)\1\s*\)")
REF_RE = re.compile(
    r"(?<=[\"'(\s=,])(?:https?://(?:www\.)?victory\.org\.il/|/|(?:\.\./)*)"
    r"wp-content/(cache/wpfc-minified/|uploads/elementor/css/)"
)


def fix_css_urls(text, old_rel):
    """Make relative url() values absolute, as seen from the file's old place."""
    base = "/" + posixpath.dirname(old_rel)

    def repl(m):
        quote, value = m.group(1), m.group(2).strip()
        if re.match(r"^(data:|https?:|//|/|#)", value):
            return m.group(0)
        path, sep, rest = _split(value)
        absolute = posixpath.normpath(posixpath.join(base, path))
        return "url(%s%s%s%s%s)" % (quote, absolute, sep, rest, quote)

    return URL_RE.sub(repl, text)


def _split(value):
    m = re.search(r"[?#]", value)
    if not m:
        return value, "", ""
    return value[: m.start()], value[m.start()], value[m.start() + 1 :]


def move_files():
    moved = 0
    for folder in FOLDERS:
        src_dir = os.path.join(ROOT, folder)
        if not os.path.isdir(src_dir):
            continue
        for dirpath, _, files in os.walk(src_dir):
            for name in files:
                src = os.path.join(dirpath, name)
                old_rel = os.path.relpath(src, ROOT).replace(os.sep, "/")
                new_rel = NEW_BASE + old_rel[len("wp-content/"):]
                dst = os.path.join(ROOT, new_rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if name.endswith(".css"):
                    with open(src, encoding="utf-8", errors="surrogateescape") as f:
                        text = f.read()
                    with open(dst, "w", encoding="utf-8", errors="surrogateescape") as f:
                        f.write(fix_css_urls(text, old_rel))
                    os.remove(src)
                else:
                    shutil.move(src, dst)
                moved += 1
        # remove folders left empty
        for dirpath, _, _ in sorted(os.walk(src_dir), key=lambda w: -len(w[0])):
            if not os.listdir(dirpath):
                os.rmdir(dirpath)
    return moved


def fix_pages():
    changed = 0
    for dirpath, _, files in os.walk(ROOT):
        for name in files:
            if not name.endswith(".html"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8", errors="surrogateescape") as f:
                text = f.read()
            new = REF_RE.sub(lambda m: "/" + NEW_BASE + m.group(1), text)
            if new != text:
                with open(path, "w", encoding="utf-8", errors="surrogateescape") as f:
                    f.write(new)
                changed += 1
    return changed


if __name__ == "__main__":
    print("moved files:", move_files())
    print("pages updated:", fix_pages())
