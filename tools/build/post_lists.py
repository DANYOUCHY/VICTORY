"""Lists of posts that the build makes from data/posts.json, so no page keeps a hand copy.

Two lists:
  recent posts  the sidebar on every post: the newest posts, without the post itself
  blog pages    the grid of posts on /blog/, /blog/2/ ... with the page numbers under it
"""
import html
import json
from functools import lru_cache
from pathlib import Path

BASE = 'https://www.victory.org.il'
PER_PAGE = 8
SIDEBAR_COUNT = 3
DEFAULT_AUTHOR = 'יוחי דנחי'
ARTICLE_CLASS = ('elementor-post elementor-grid-item post-%d post type-post status-publish '
                 'format-standard has-post-thumbnail hentry category-uncategorized')
LIST_OPEN = ('\n\t\t\t<div class="elementor-posts-container elementor-posts '
             'elementor-posts--skin-classic elementor-grid" role="list">\n')
LIST_CLOSE = '\t\t\t\t</div>\n'


@lru_cache(maxsize=None)
def load_posts(data_file: Path) -> tuple:
    """All posts, newest first, as data/posts.json holds them."""
    return tuple(json.loads(data_file.read_text(encoding='utf-8')))


def _text(s: str) -> str:
    return html.escape(s, quote=False)


def _attr(s: str) -> str:
    return html.escape(s, quote=True)


def _article_class(post: dict) -> str:
    return post.get('cls') or ARTICLE_CLASS % post['id']


def _paragraph(s: str) -> str:
    return '<p>%s</p>' % _text(s) if s else ''


# ---------- the recent-posts sidebar ----------

def sidebar_article(post: dict) -> str:
    """One post in the sidebar: title, short excerpt, "read more"."""
    return (
        '<article class="%s" role="listitem">\n'
        '\t\t\t\t<div class="elementor-post__text">\n'
        '\t\t\t\t<h3 class="elementor-post__title">\n\t\t\t<a href="%s" >\n\t\t\t\t%s\t\t\t</a>\n\t\t</h3>\n'
        '\t\t\t\t<div class="elementor-post__excerpt">\n\t\t\t%s\n\t\t</div>\n'
        '\t\t\n\t\t<a class="elementor-post__read-more" href="%s" aria-label="קרא עוד אודות %s" tabindex="-1" >\n'
        '\t\t\tקראו עוד...\t\t</a>\n\n\t\t\t\t</div>\n\t\t\t\t</article>\n'
    ) % (_article_class(post), post['url'], _text(post['title']),
         post.get('excerpt_short_html', ''), post['url'], _attr(post['title']))


def recent_posts(posts: tuple, own_id: int = None) -> str:
    """The sidebar list: the newest posts other than the one the page shows."""
    shown = [p for p in posts if p['id'] != own_id][:SIDEBAR_COUNT]
    return LIST_OPEN + ''.join(sidebar_article(p) for p in shown) + LIST_CLOSE + '\t\t\t\t'


# ---------- the blog pages ----------

def blog_page_count(posts: tuple) -> int:
    return max(1, -(-len(posts) // PER_PAGE))


def blog_link(n: int) -> str:
    return '/blog/' if n == 1 else '/blog/%d/' % n


def blog_article(post: dict, first_image: bool) -> str:
    """One post in the blog grid. Only the first picture on a page loads with high priority."""
    thumb = post['thumb']
    if not first_image:
        thumb = thumb.replace('fetchpriority="high" ', '')
    thumb_link = ('\t\t\t\t<a class="elementor-post__thumbnail__link" href="%s" tabindex="-1" >\n'
                  '\t\t\t<div class="elementor-post__thumbnail">%s</div>\n\t\t</a>\n'
                  % (post['url'], thumb)) if thumb else ''
    return (
        '<article class="%s" role="listitem">\n'
        '%s'
        '\t\t\t\t<div class="elementor-post__text">\n'
        '\t\t\t\t<h3 class="elementor-post__title">\n\t\t\t<a href="%s" >\n\t\t\t\t%s\t\t\t</a>\n\t\t</h3>\n'
        '\t\t\t\t<div class="elementor-post__meta-data">\n\t\t\t\t\t<span class="elementor-post-author">\n'
        '\t\t\t%s\t\t</span>\n\t\t\t\t</div>\n'
        '\t\t\t\t<div class="elementor-post__excerpt">\n\t\t\t%s\n\t\t</div>\n'
        '\t\t\n\t\t<a class="elementor-post__read-more" href="%s" aria-label="קרא עוד אודות %s" tabindex="-1" >\n'
        '\t\t\tקראו עוד »\t\t</a>\n\n\t\t\t\t</div>\n\t\t\t\t</article>\n'
    ) % (_article_class(post), thumb_link, post['url'], _text(post['title']),
         _text(post['author'] or DEFAULT_AUTHOR), post.get('excerpt_html', _paragraph(post['excerpt'])),
         post['url'], _attr(post['title']))


def pagination(page: int, last: int) -> str:
    """The "previous / 1 2 3 / next" row under the blog grid."""
    parts = [('<a class="page-numbers prev" href="%s">&laquo; הקודם</a>' % blog_link(page - 1)) if page > 1
             else '<span class="page-numbers prev">&laquo; הקודם</span>']
    for n in range(1, last + 1):
        if n == page:
            parts.append('<span aria-current="page" class="page-numbers current">'
                         '<span class="elementor-screen-only">עמוד</span>%d</span>' % n)
        else:
            parts.append('<a class="page-numbers" href="%s">'
                         '<span class="elementor-screen-only">עמוד</span>%d</a>' % (blog_link(n), n))
    parts.append(('<a class="page-numbers next" href="%s">הבא &raquo;</a>' % blog_link(page + 1)) if page < last
                 else '<span class="page-numbers next">הבא &raquo;</span>')
    return ('\t\t<div class="e-load-more-anchor" data-page="%d" data-max-page="%d" data-next-page="%s"></div>\n'
            '\t\t\t\t<nav class="elementor-pagination" aria-label="עימוד">\n\t\t\t%s\t\t</nav>\n'
            ) % (page, last, BASE + blog_link(min(page + 1, last)), ' \n'.join(parts))


def blog_list(posts: tuple, page: int) -> str:
    """The grid of one blog page (page 1 is /blog/), with the page numbers."""
    chunk = posts[(page - 1) * PER_PAGE:page * PER_PAGE]
    first = next((i for i, p in enumerate(chunk) if p['thumb']), -1)
    return (LIST_OPEN + ''.join(blog_article(p, i == first) for i, p in enumerate(chunk))
            + LIST_CLOSE + pagination(page, blog_page_count(posts)) + '\t\t\t\t')


def list_params(data_file: Path, params: dict) -> dict:
    """The generated lists a page asks for: {{recent_posts}} on a post, {{blog_list}} on a blog page."""
    out = {}
    if 'post_id' in params:
        out['recent_posts'] = recent_posts(load_posts(data_file), int(params['post_id']))
    if 'blog_page' in params:
        out['blog_list'] = blog_list(load_posts(data_file), int(params['blog_page']))
    return out
