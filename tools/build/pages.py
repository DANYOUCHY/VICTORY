"""Finding the pages in src/pages and reading what each one says about itself."""
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Page:
    name: str          # the folder under src/pages, e.g. "home" or "posts/hermit-crab"
    folder: Path       # src/pages/<name>
    output: str        # where the built page goes, under site/ (e.g. "index.html")
    params: dict       # the page's own values for {{...}} in the components
    layout: Path       # the page's layout: its own page.html, or a shared one named in page.json


def load_page(folder: Path, pages_root: Path) -> Page:
    """Read src/pages/<name>/page.json. "layout" (a path from src/) shares one layout among many pages."""
    data = json.loads((folder / 'page.json').read_text(encoding='utf-8'))
    layout = pages_root.parent / data['layout'] if 'layout' in data else folder / 'page.html'
    return Page(folder.relative_to(pages_root).as_posix(), folder, data['output'], data.get('params', {}), layout)


def find_pages(src_root: Path, names: list = None) -> list:
    """All pages (any folder under src/pages with a page.json), or only the ones asked for by name."""
    pages_root = src_root / 'pages'
    folders = sorted(p.parent for p in pages_root.rglob('page.json'))
    pages = [load_page(f, pages_root) for f in folders]
    if names:
        missing = set(names) - {p.name for p in pages}
        if missing:
            raise SystemExit(f'No such page in src/pages: {", ".join(sorted(missing))}')
        pages = [p for p in pages if p.name in names]
    return pages
