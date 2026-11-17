"""Putting one page together: its layout file, its parameters and the menu."""
from pathlib import Path

from .menu import menu_params
from .pages import Page
from .template import read_source, render


def build_page(page: Page, src_root: Path) -> str:
    """The finished HTML of one page."""
    params = dict(page.params)
    params.update(menu_params(src_root, params))
    layout = read_source(page.folder / 'page.html')
    return render(layout, params, src_root, where=f'pages/{page.name}/page.html')
