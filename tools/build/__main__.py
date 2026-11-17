"""Build the site's pages from src/ into site/.

    python -m tools.build              build every page in src/pages
    python -m tools.build home         build only these pages
    python -m tools.build --check      write nothing; report pages that differ from site/

Run from the root of the repository. See src/README.md.
"""
import argparse
import sys
from pathlib import Path

from .output import current_text, first_difference, write_page
from .pages import find_pages
from .render import build_page
from .template import TemplateError

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
SITE = ROOT / 'site'


def parse_args(argv):
    parser = argparse.ArgumentParser(prog='python -m tools.build', description=__doc__.splitlines()[0])
    parser.add_argument('pages', nargs='*', help='page names (folders in src/pages); default: all')
    parser.add_argument('--check', action='store_true', help='compare with site/ without writing')
    return parser.parse_args(argv)


def check(pages) -> int:
    """Report every page whose build differs from site/. Exit code 1 if any does."""
    differ = 0
    for page in pages:
        html, old = build_page(page, SRC), current_text(SITE / page.output)
        if html == old:
            print(f'same      {page.output}')
        else:
            differ += 1
            print(f'DIFFERENT {page.output}  ({first_difference(old, html)})')
    return 1 if differ else 0


def build(pages) -> int:
    for page in pages:
        changed = write_page(SITE / page.output, build_page(page, SRC))
        print(f'{"written  " if changed else "unchanged"} {page.output}')
    return 0


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        pages = find_pages(SRC, args.pages)
        return check(pages) if args.check else build(pages)
    except TemplateError as e:
        print(f'error: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
