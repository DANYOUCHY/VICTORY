"""Finding the pages in src/pages and reading what each one says about itself."""
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Page:
    name: str          # the folder name under src/pages, e.g. "home"
    folder: Path       # src/pages/<name>
    output: str        # where the built page goes, under site/ (e.g. "index.html")
    params: dict       # the page's own values for {{...}} in the components


def load_page(folder: Path) -> Page:
    """Read src/pages/<name>/page.json."""
    data = json.loads((folder / 'page.json').read_text(encoding='utf-8'))
    return Page(folder.name, folder, data['output'], data.get('params', {}))


def find_pages(src_root: Path, names: list = None) -> list:
    """All pages (folders with a page.json), or only the ones asked for by name."""
    folders = sorted(p.parent for p in (src_root / 'pages').glob('*/page.json'))
    pages = [load_page(f) for f in folders]
    if names:
        missing = set(names) - {p.name for p in pages}
        if missing:
            raise SystemExit(f'No such page in src/pages: {", ".join(sorted(missing))}')
        pages = [p for p in pages if p.name in names]
    return pages
