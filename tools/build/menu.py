"""The top menu, written once in src/components/header/menu.json and drawn here.

Each page says which item is its own ("active_menu" in page.json); that item gets
WordPress's "current page" classes, exactly as the old pages had them.
"""
import json
from pathlib import Path

from .template import TemplateError

ACTIVE_LI = ' current-menu-item page_item page-item-{page_id} current_page_item'


def load_menu(src_root: Path) -> list:
    """The menu items, in order."""
    path = src_root / 'components' / 'header' / 'menu.json'
    return json.loads(path.read_text(encoding='utf-8'))['items']


def item_href(item: dict, home_url: str) -> str:
    """Where the item links to; "@home" is the home page, relative to the current page."""
    return home_url if item['href'] == '@home' else item['href']


def render_item(item: dict, active: bool, home_url: str, in_dropdown: bool) -> str:
    """One <li> of the menu."""
    if active and item.get('page_id') is None:
        raise TemplateError(f'menu.json: item "{item["key"]}" is active on this page but has no page_id')
    li_class = item['classes'] + (ACTIVE_LI.format(page_id=item['page_id']) if active else '') + ' ' + item['id_class']
    aria = ' aria-current="page"' if active else ''
    a_class = 'elementor-item elementor-item-active menu-link' if active else 'elementor-item menu-link'
    tabindex = ' tabindex="-1"' if in_dropdown else ''
    return (f'<li class="{li_class}"><a href="{item_href(item, home_url)}"{aria} '
            f'class="{a_class}"{tabindex}>{item["label"]}</a></li>')


def render_menu(items: list, active_key: str, home_url: str, in_dropdown: bool = False) -> str:
    """All the items, one per line. The header shows the menu twice: the bar and the phone dropdown."""
    return '\n'.join(render_item(i, i['key'] == active_key, home_url, in_dropdown) for i in items)


def menu_params(src_root: Path, params: dict) -> dict:
    """The two ready-made menus, as parameters for the header."""
    items = load_menu(src_root)
    active, home = params.get('active_menu', ''), params['home_url']
    return {'menu': render_menu(items, active, home),
            'menu_dropdown': render_menu(items, active, home, in_dropdown=True)}
