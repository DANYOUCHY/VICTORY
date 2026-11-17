"""Fill the sidebar YouTube list with the channel's latest videos.

Reads the channel's public RSS feed (no API key) and writes the same markup the
WordPress plugin produced, so the existing styles and player script keep working.
Run by .github/workflows/youtube-feed.yml every 6 hours.

The list lives in one file, src/components/youtube/items.html. This tool writes it,
rebuilds the pages from src/ (tools/build), and also updates any page in site/ that
still holds its own copy of the list (a page not yet built from src/).

Usage: python3 tools/youtube_feed.py site feed.xml
"""
import glob
import html
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build.__main__ import main as build_pages   # noqa: E402

CHANNEL = 'UCcszsZ1SGDe5uRXQoooU8vQ'
COUNT = 5
COMPONENT = ROOT / 'src' / 'components' / 'youtube' / 'items.html'
NS = {'a': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
YT_SVG = ('<svg aria-hidden="true" focusable="false" data-prefix="fab" data-icon="youtube" role="img" '
          'xmlns="http://www.w3.org/2000/svg" viewBox="0 0 576 512" class="svg-inline--fa fa-youtube fa-w-18">'
          '<path fill="currentColor" d="M549.655 124.083c-6.281-23.65-24.787-42.276-48.284-48.597C458.781 64 288 64 288 64S117.22 64 74.629 75.486c-23.497 6.322-42.003 24.947-48.284 48.597-11.412 42.867-11.412 132.305-11.412 132.305s0 89.438 11.412 132.305c6.281 23.65 24.787 41.5 48.284 47.821C117.22 448 288 448 288 448s170.78 0 213.371-11.486c23.497-6.321 42.003-24.171 48.284-47.821 11.412-42.867 11.412-132.305 11.412-132.305s0-89.438-11.412-132.305zm-317.51 213.508V175.185l142.739 81.205-142.739 81.201z"></path></svg>')
# everything from the list up to the end of the feed box, whatever is there now
WRAP = re.compile(
    r'<div class="sby_items_wrap" role="list">.*?'
    r'(?=</div>\s*<style type="text/css">body #sb_youtube_)', re.S)


def read_entries(feed_file):
    """The newest videos in the feed."""
    return ET.parse(feed_file).getroot().findall('a:entry', NS)[:COUNT]


def video_item(e):
    """One video in the list: thumbnail, title, play button."""
    vid = e.find('yt:videoId', NS).text
    title = html.escape(e.find('a:title', NS).text or '', quote=True)
    ts = int(datetime.fromisoformat(e.find('a:published', NS).text).timestamp())
    img = 'https://i1.ytimg.com/vi/%s/' % vid
    srcset = html.escape('{"120":"%sdefault.jpg","320":"%smqdefault.jpg","480":"%shqdefault.jpg","640":"%ssddefault.jpg"}'
                         % ((img.replace('/', '\\/'),) * 4), quote=True)
    return (
        '<div class="sby_item" role="listitem" id="sby_%s_%s" data-date="%d" data-video-id="%s" style="margin-bottom: 5px;">'
        '<div class="sby_inner_item"><div class="sby_video_thumbnail_wrap sby_item_video_thumbnail_wrap">'
        '<a class="sby_video_thumbnail sby_item_video_thumbnail" href="https://www.youtube.com/watch?v=%s" target="_blank" rel="noopener"'
        ' data-full-res="%smaxresdefault.jpg" data-img-src-set="%s" data-video-id="%s" data-video-title="%s">'
        '<img src="%shqdefault.jpg" alt="%s" loading="lazy">'
        '<div class="sby_thumbnail_hover sby_item_video_thumbnail_hover"><div class="sby_thumbnail_hover_inner">'
        '<span class="sby_video_title" role="heading" aria-level="3">%s</span></div></div>'
        '<div class="sby_play_btn"><span class="sby_play_btn_bg"></span>%s</div>'
        '<span class="sby_loader sby_hidden" style="background-color: rgb(255, 255, 255);"></span></a>'
        '<div id="sby_player_%s" class="sby_player_wrap"></div></div></div></div>'
    ) % (CHANNEL, vid, ts, vid, vid, img, srcset, vid, title, img, title, title, YT_SVG, vid)


def list_footer():
    """Same footer as the plugin. "Load More" opens the channel's video page; the inline
    handler runs first and stops the plugin's script, which would ask WordPress for more."""
    return ('<div class="sby_footer">'
            '<div class="sby-screenreader" role="status" aria-live="polite" aria-atomic="true" data-sby-feed-status=""></div>'
            '<button type="button" aria-label="Load more content" class="sby_load_btn" '
            'onclick="event.stopImmediatePropagation();window.open(\'https://www.youtube.com/channel/%s/videos\',\'_blank\',\'noopener\');return false;">'
            '<span class="sby_btn_text">Load More...</span>'
            '<span class="sby_loader sby_hidden" style="background-color: rgb(255, 255, 255);"></span></button>'
            '<span class="sby_follow_btn">'
            '<a href="https://www.youtube.com/channel/%s/" target="_blank" rel="noopener">%s<span>Subscribe</span></a>'
            '</span></div>') % (CHANNEL, CHANNEL, YT_SVG)


def video_list(entries):
    """The whole list as it sits in a page (ends with a newline, before the box closes)."""
    items = ''.join(video_item(e) for e in entries)
    return '<div class="sby_items_wrap" role="list">%s</div>%s\n' % (items, list_footer())


def write_component(block):
    """Save the list into src/; True if it changed. (The file's own final newline is not content.)"""
    old = COMPONENT.read_text(encoding='utf-8') if COMPONENT.exists() else ''
    new = block + '\n'
    if old == new:
        return False
    COMPONENT.parent.mkdir(parents=True, exist_ok=True)
    COMPONENT.write_text(new, encoding='utf-8', newline='\n')
    return True


def update_own_copies(root, block):
    """Pages in site/ that still hold their own copy of the list; returns how many changed."""
    changed = 0
    for f in glob.glob(os.path.join(root, '**', '*.html'), recursive=True):
        t = open(f, encoding='utf-8').read()
        if 'sby_items_wrap' not in t:
            continue
        n = WRAP.sub(lambda m: block, t)
        if n != t:
            open(f, 'w', encoding='utf-8', newline='\n').write(n)
            changed += 1
    return changed


def main(root, feed_file):
    entries = read_entries(feed_file)
    if not entries:
        sys.exit('feed has no videos; pages left unchanged')
    block = video_list(entries)
    if write_component(block):
        print('video list changed; rebuilding pages from src/')
        if build_pages([]) != 0:
            sys.exit('building the pages failed')
    print('videos:', len(entries), '| pages with their own copy updated:', update_own_copies(root, block))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
