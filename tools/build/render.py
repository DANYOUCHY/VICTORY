"""Putting one page together: its layout file, its parameters, the menu and the lists of posts."""
import json
from pathlib import Path

from .menu import menu_params
from .pages import Page
from .post_lists import list_params
from .template import read_source, render

DEFAULTS_FILE = 'components/defaults.json'   # values every page has unless its page.json says otherwise
POSTS_DATA = Path('data') / 'posts.json'      # beside src/, the list of all blog posts


def page_params(page: Page, src_root: Path) -> dict:
    """Defaults, then the page's own values, then what the build makes (menu, post lists)."""
    defaults_path = src_root / DEFAULTS_FILE
    params = json.loads(defaults_path.read_text(encoding='utf-8')) if defaults_path.is_file() else {}
    params['page_dir'] = f'pages/{page.name}'   # the page's own folder, for {{> {{page_dir}}/file.html}}
    params.update(page.params)
    params.update(menu_params(src_root, params))
    params.update(list_params(src_root.parent / POSTS_DATA, params))
    return params


def build_page(page: Page, src_root: Path) -> str:
    """The finished HTML of one page."""
    layout = read_source(page.layout)
    return render(layout, page_params(page, src_root), src_root, where=page.layout.relative_to(src_root).as_posix())
