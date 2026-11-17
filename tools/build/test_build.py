"""Checks for the build tool.  Run:  python -m unittest tools.build.test_build"""
import tempfile
import unittest
from pathlib import Path

from .__main__ import SITE, SRC
from .menu import render_item
from .output import current_text
from .pages import find_pages
from .render import build_page
from .template import TemplateError, render


def make_src(files: dict) -> Path:
    """A throwaway src/ folder with the given files."""
    root = Path(tempfile.mkdtemp())
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding='utf-8')
    return root


class TemplateTests(unittest.TestCase):
    def test_param(self):
        self.assertEqual(render('<a href="{{home}}">', {'home': './'}, Path('.')), '<a href="./">')

    def test_missing_param_stops(self):
        with self.assertRaises(TemplateError):
            render('{{nothing}}', {}, Path('.'))

    def test_include_drops_final_newline(self):
        src = make_src({'part.html': '<b>x</b>\n'})
        self.assertEqual(render('[{{> part.html}}]', {}, src), '[<b>x</b>]')

    def test_include_with_args(self):
        src = make_src({'d.html': '<hr id="{{id}}">'})
        self.assertEqual(render('{{> d.html id=7}}', {}, src), '<hr id="7">')

    def test_missing_include_stops(self):
        with self.assertRaises(TemplateError):
            render('{{> nope.html}}', {}, make_src({}))

    def test_include_loop_stops(self):
        with self.assertRaises(TemplateError):
            render('{{> a.html}}', {}, make_src({'a.html': '{{> a.html}}'}))


class MenuTests(unittest.TestCase):
    ITEM = {'key': 'blog', 'label': 'בלוג', 'href': '/blog/', 'classes': 'menu-item', 'id_class': 'menu-item-488', 'page_id': 61}

    def test_active_item(self):
        html = render_item(self.ITEM, True, './', False)
        self.assertIn('current-menu-item page_item page-item-61 current_page_item menu-item-488', html)
        self.assertIn('aria-current="page"', html)

    def test_home_link_is_relative(self):
        item = dict(self.ITEM, href='@home')
        self.assertIn('href="../"', render_item(item, False, '../', False))


class SiteTests(unittest.TestCase):
    def test_built_pages_match_site(self):
        """Every page built from src/ is exactly what site/ holds."""
        for page in find_pages(SRC):
            with self.subTest(page=page.name):
                self.assertEqual(build_page(page, SRC), current_text(SITE / page.output))


if __name__ == '__main__':
    unittest.main()
