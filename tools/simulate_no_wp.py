#!/usr/bin/env python3
"""Load every page of the static site with WordPress gone, and report what breaks.

Every request to www.victory.org.il is answered only from the site/ folder (the way
the server does it), so anything WordPress would have supplied shows up as a miss.
Each page is opened at desktop and phone size, scrolled to the end so lazy images
and scripts load, and the site-wide popup is opened.

Usage: python3 tools/simulate_no_wp.py site [out.json] [--only path1,path2]
"""
import asyncio
import json
import mimetypes
import os
import sys
from collections import defaultdict
from urllib.parse import unquote, urlparse

from playwright.async_api import async_playwright

ROOT = sys.argv[1] if len(sys.argv) > 1 else 'site'
OUT = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else None
ONLY = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else None
HOSTS = {'www.victory.org.il', 'victory.org.il'}
WP_ONLY = ('wp-json', 'admin-ajax.php', 'xmlrpc.php', 'wp-login.php', '/wp-admin', 'wp-cron.php')

misses = defaultdict(set)       # path -> pages
wp_calls = defaultdict(set)     # path -> pages
external = defaultdict(int)     # host -> count
console_errors = defaultdict(set)
mimetypes.add_type('image/webp', '.webp')
mimetypes.add_type('font/woff2', '.woff2')
mimetypes.add_type('application/javascript', '.js')


def local_file(path):
    p = unquote(path).lstrip('/')
    f = os.path.join(ROOT, p)
    if p == '' or p.endswith('/'):
        f = os.path.join(f, 'index.html')
    if os.path.isfile(f):
        return f
    if os.path.isfile(os.path.join(f, 'index.html')):
        return os.path.join(f, 'index.html')
    return None


async def handle(route, request, page_name):
    u = urlparse(request.url)
    if u.scheme in ('data', 'blob'):
        return await route.continue_()
    if u.netloc not in HOSTS:
        external[u.netloc] += 1
        return await route.abort()
    full = u.path + ('?' + u.query if u.query else '')
    if any(w in full for w in WP_ONLY) or u.path.startswith(('/wp-content/', '/wp-includes/')):
        wp_calls[full.split('?')[0] if 'admin-ajax' not in full else full[:120]].add(page_name)
        return await route.fulfill(status=404, body='')
    f = local_file(u.path)
    if not f:
        misses[unquote(u.path)].add(page_name)
        return await route.fulfill(status=404, body='')
    ctype = mimetypes.guess_type(f)[0] or 'application/octet-stream'
    with open(f, 'rb') as fh:
        body = fh.read()
    await route.fulfill(status=200, body=body, headers={'content-type': ctype})


async def visit(browser, path, size, sem):
    async with sem:
        ctx = await browser.new_context(viewport=size, is_mobile=size['width'] < 768,
                                        has_touch=size['width'] < 768, locale='he-IL')
        page = await ctx.new_page()
        name = path + (' [phone]' if size['width'] < 768 else '')
        await page.route('**/*', lambda r, q: handle(r, q, name))
        page.on('console', lambda m: console_errors[m.text[:160]].add(name) if m.type == 'error' and 'net::ERR' not in m.text and 'Failed to load resource' not in m.text else None)
        page.on('pageerror', lambda e: console_errors['JS: ' + str(e)[:160]].add(name))
        try:
            await page.goto('https://www.victory.org.il' + path, wait_until='load', timeout=30000)
            await page.wait_for_timeout(600)
            for sel in ('#scb-btn-reject', '.scb-btn-accept'):   # cookie banner
                btn = page.locator(sel).first
                if await btn.count() and await btn.is_visible():
                    await btn.click(timeout=3000)
                    await page.wait_for_timeout(300)
                    break
            for _ in range(12):
                await page.mouse.wheel(0, 900)
                await page.wait_for_timeout(250)
            await page.wait_for_timeout(800)
            # open the site-wide popup the way a visitor would
            link = page.locator('a[href*="popup%3Aopen"]').first
            if await link.count():
                try:
                    await link.scroll_into_view_if_needed(timeout=3000)
                    await link.click(timeout=3000)
                    await page.wait_for_timeout(1200)
                except Exception:
                    await page.evaluate("document.querySelector('a[href*=\"popup%3Aopen\"]').click()")
                    await page.wait_for_timeout(1200)
            # open an image in the lightbox and play a video from the YouTube feed
            for sel in ('a[href*="lightbox%26settings"]', '.sby_item .sby_video_thumbnail'):
                el = page.locator(sel).first
                if await el.count():
                    try:
                        await page.keyboard.press('Escape')
                        await el.scroll_into_view_if_needed(timeout=3000)
                        await el.click(timeout=3000)
                        await page.wait_for_timeout(1200)
                    except Exception:
                        pass
            await page.wait_for_load_state('networkidle', timeout=8000)
        except Exception as e:
            console_errors['LOAD: ' + str(e)[:120]].add(name)
        await ctx.close()


async def main():
    pages = []
    for dirpath, _, files in os.walk(ROOT):
        if 'index.html' in files:
            rel = os.path.relpath(dirpath, ROOT).replace(os.sep, '/')
            if rel.startswith(('wp-content', 'wp-includes', 'assets', 'comments-api', 'contact-api', 'deploy-api')):
                continue
            pages.append('/' if rel == '.' else '/' + rel + '/')
    pages.append('/404.html')
    if ONLY:
        pages = ONLY
    pages.sort()
    sem = asyncio.Semaphore(6)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        jobs = [visit(browser, pg, sz, sem) for pg in pages
                for sz in ({'width': 1366, 'height': 900}, {'width': 390, 'height': 844})]
        await asyncio.gather(*jobs)
        await browser.close()
    rep = {
        'pages': len(pages),
        'missing_files': {k: sorted(v)[:3] + ([f'+{len(v) - 3}'] if len(v) > 3 else []) for k, v in sorted(misses.items())},
        'wordpress_calls': {k: sorted(v)[:3] + ([f'+{len(v) - 3}'] if len(v) > 3 else []) for k, v in sorted(wp_calls.items())},
        'external_hosts': dict(sorted(external.items(), key=lambda x: -x[1])),
        'console_errors': {k: sorted(v)[:3] + ([f'+{len(v) - 3}'] if len(v) > 3 else []) for k, v in sorted(console_errors.items())},
    }
    if OUT:
        json.dump(rep, open(OUT, 'w'), ensure_ascii=False, indent=1)
    print('pages:', rep['pages'])
    for key in ('missing_files', 'wordpress_calls', 'console_errors'):
        print(f'\n{key}: {len(rep[key])}')
        for k, v in list(rep[key].items())[:60]:
            print('  ', k[:150], '<-', v[:2], v[3:] if len(v) > 3 else '')
    print('\nexternal hosts (blocked in this test):', rep['external_hosts'])


asyncio.run(main())
