"""Compare every page of the static site with the WordPress site, on phone and desktop.

For each page and width it loads both versions in a real browser and compares
every visible Elementor widget (type and height), the page height, fonts that
failed, images that failed and script errors. Writes reports/compare.md.

Usage: python3 tools/compare.py site https://candidate.example [WordPress base]
"""
import asyncio
import glob
import json
import os
import sys
import urllib.parse

from playwright.async_api import async_playwright

root, CAND = sys.argv[1], sys.argv[2].rstrip('/')
LIVE = (sys.argv[3] if len(sys.argv) > 3 else 'https://www.victory.org.il').rstrip('/')
BYPASS = {'X-Static-Bypass': 'wp-origin-7f3k'}
WIDTHS = [375, 1366]
TOL = 6  # px

paths = []
for f in sorted(glob.glob(os.path.join(root, '**', 'index.html'), recursive=True)):
    rel = os.path.relpath(os.path.dirname(f), root)
    if rel.startswith(('wp-', 'thanks')):
        continue
    paths.append('/' if rel == '.' else '/' + urllib.parse.quote(rel) + '/')

MEASURE = r"""async () => {
  document.querySelectorAll('#scb-banner,#scb-overlay,#wpadminbar').forEach(e => e.remove());
  await document.fonts.ready;
  const vis = e => { const s = getComputedStyle(e); return e.offsetParent !== null && s.visibility !== 'hidden' && s.display !== 'none'; };
  const widgets = [...document.querySelectorAll('.elementor-widget')]
    .filter(w => !w.closest('.elementor-sticky__spacer') && !w.closest('.elementor-location-popup') && vis(w))
    .map(w => [w.dataset.widget_type || '?', Math.round(w.getBoundingClientRect().height), (w.innerText || '').trim().slice(0, 40)])
    .filter(w => w[1] > 0);
  const badFonts = [...new Set([...document.fonts].filter(f => f.status === 'error').map(f => f.family))];
  const badImgs = [...document.images].filter(i => i.complete && i.naturalWidth === 0 && vis(i) && !/ytimg|facebook|gravatar|google/.test(i.src)).map(i => i.src.slice(-60));
  return {h: document.documentElement.scrollHeight, sw: document.documentElement.scrollWidth, widgets, badFonts, badImgs};
}"""

async def measure(ctx, url, headers=None):
    pg = await ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)[:100]))
    if headers:
        await pg.set_extra_http_headers(headers)
    try:
        await pg.goto(url, wait_until='networkidle', timeout=60000)
        await pg.wait_for_timeout(1500)
        r = await pg.evaluate(MEASURE)
        r['errors'] = errs
        r['title'] = await pg.title()
    except Exception as e:
        r = {'fail': str(e)[:150]}
    await pg.close()
    return r

def diff(a, b):
    out = []
    if 'fail' in a or 'fail' in b:
        return ['load failed: live=%s static=%s' % (a.get('fail', 'ok'), b.get('fail', 'ok'))]
    if a['title'] != b['title']:
        out.append('title differs: "%s" vs "%s"' % (a['title'], b['title']))
    wa, wb = a['widgets'], b['widgets']
    if [w[0] for w in wa] != [w[0] for w in wb]:
        ta, tb = [w[0] for w in wa], [w[0] for w in wb]
        out.append('widgets differ: only in WordPress %s | only in static %s'
                   % (sorted(set(ta) - set(tb)) or [x for x in ta if ta.count(x) != tb.count(x)][:5],
                      sorted(set(tb) - set(ta)) or [x for x in tb if ta.count(x) != tb.count(x)][:5]))
    else:
        for x, y in zip(wa, wb):
            if abs(x[1] - y[1]) > max(TOL, 0.02 * x[1]):
                out.append('%s "%s": %dpx in WordPress, %dpx static' % (x[0], x[2], x[1], y[1]))
    if b['sw'] > a['sw']:
        out.append('static page scrolls sideways (%d > %d)' % (b['sw'], a['sw']))
    for k, name in (('badFonts', 'fonts failed'), ('badImgs', 'images failed'), ('errors', 'script errors')):
        extra = [v for v in b[k] if v not in a[k]]
        if extra:
            out.append('%s on static: %s' % (name, extra[:3]))
    return out

async def main():
    results = []
    sem = asyncio.Semaphore(4)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctxs = {w: await browser.new_context(viewport={'width': w, 'height': 900}, is_mobile=w < 768) for w in WIDTHS}

        async def one(path, w):
            async with sem:
                a = await measure(ctxs[w], LIVE + path, BYPASS)
                b = await measure(ctxs[w], CAND + path)
                results.append((path, w, diff(a, b)))
        await asyncio.gather(*(one(pth, w) for pth in paths for w in WIDTHS))
        await browser.close()

    results.sort()
    bad = [r for r in results if r[2]]
    os.makedirs('reports', exist_ok=True)
    with open('reports/compare.md', 'w', encoding='utf-8') as f:
        f.write('# Static vs WordPress\n\nPages: %d, checks: %d, with differences: %d\n\n' % (len(paths), len(results), len(bad)))
        for path, w, d in bad:
            f.write('## %s (%dpx)\n' % (urllib.parse.unquote(path), w))
            for line in d:
                f.write('- %s\n' % line)
            f.write('\n')
    json.dump(results, open('reports/compare.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('pages', len(paths), 'checks', len(results), 'with differences', len(bad))

asyncio.run(main())
