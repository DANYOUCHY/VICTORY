#!/usr/bin/env python3
"""The page "התמונות של החיים" (/life-pictures/): a carousel of insight pictures that
visitors can download, print and share.

The list of pictures is data/life-pictures.json. To add a picture: add an entry there
(file = next free life-NN, src = the original image's file name, name = short name for
the downloaded file, alt = the picture's text), then run both steps:

  python3 tools/life_pictures.py images "<folder with the original images>"
  python3 tools/life_pictures.py page

"images" makes, for each picture, the original (.png, for download and print), a .jpg
for sharing and two .webp sizes for the page, in site/assets/life-pictures/.
"page" builds site/life-pictures/index.html from the services page (same header, footer,
menu and popup), so it stays in the site's design.
"""
import html
import json
import os
import re
import shutil
import sys

ROOT = 'site'
DATA = 'data/life-pictures.json'
OUT_DIR = os.path.join(ROOT, 'assets', 'life-pictures')
TEMPLATE = os.path.join(ROOT, 'my-services', 'index.html')
BASE = 'https://www.victory.org.il'


def load():
    with open(DATA, encoding='utf-8') as f:
        return json.load(f)


def cmd_images(src_dir):
    from PIL import Image
    os.makedirs(OUT_DIR, exist_ok=True)
    for p in load()['pictures']:
        src = os.path.join(src_dir, p['src'])
        base = os.path.join(OUT_DIR, p['file'])
        shutil.copyfile(src, base + '.png')
        im = Image.open(src).convert('RGB')
        im.save(base + '.jpg', 'JPEG', quality=88, optimize=True, progressive=True)
        for width in (600, 1100):
            copy = im.copy()
            if copy.width > width:
                copy = copy.resize((width, round(copy.height * width / copy.width)), Image.LANCZOS)
            copy.save('%s-%d.webp' % (base, width), 'WEBP', quality=82, method=6)
        print(p['file'], im.size)


def esc(s):
    return html.escape(s, quote=True)


def slides_html(pics):
    from PIL import Image
    out = []
    total = len(pics)
    for i, p in enumerate(pics, 1):
        url = '/assets/life-pictures/' + p['file']
        w, h = Image.open(os.path.join(OUT_DIR, p['file'] + '-1100.webp')).size
        lazy = '' if i == 1 else ' loading="lazy"'
        fetch = ' fetchpriority="high"' if i == 1 else ''
        out.append(
            f'<figure class="lp-slide" id="lp-{i}" role="group" aria-roledescription="שקופית" '
            f'aria-label="{i} מתוך {total}" data-name="{esc(p["name"])}" data-png="{url}.png" data-jpg="{url}.jpg">'
            f'<a class="lp-open" href="{url}.png" target="_blank" rel="noopener" aria-label="פתיחת התמונה בגודל מלא">'
            f'<img src="{url}-1100.webp" srcset="{url}-600.webp 600w, {url}-1100.webp 1100w" '
            f'sizes="(max-width: 767px) 92vw, 760px" width="{w}" height="{h}" alt="{esc(p["alt"])}" '
            f'decoding="async"{lazy}{fetch}></a></figure>')
    return '\n'.join(out)


CSS = """<style id="lp-css">
.lp-intro .elementor-widget-container{text-align:center}
.lp-intro p{margin-bottom:.35em}
.lp-section{padding:10px 15px 60px}
.lp-wrap{max-width:1000px;margin:0 auto}
.lp-carousel{display:flex;align-items:center;gap:12px}
.lp-track{flex:1;min-width:0;display:flex;align-items:flex-start;overflow-x:auto;overflow-y:hidden;transition:height .3s;scroll-snap-type:x mandatory;scroll-behavior:smooth;scrollbar-width:none;border-radius:18px;background:#f2f6f8;outline:none}
.lp-track::-webkit-scrollbar{display:none}
.lp-track:focus-visible{box-shadow:0 0 0 3px #14AED0}
.lp-slide{flex:0 0 100%;margin:0;scroll-snap-align:center;scroll-snap-stop:always;display:flex;align-items:center;justify-content:center;height:min(72vh,680px);padding:18px;box-sizing:border-box}
.lp-open{display:flex;align-items:center;justify-content:center;width:100%;height:100%}
.lp-slide img{max-width:100%;max-height:100%;width:auto;height:auto;object-fit:contain;border-radius:8px;box-shadow:0 6px 24px rgba(0,0,0,.18)}
.lp-arrow{flex:0 0 auto;width:48px;height:48px;border-radius:50%;border:0;padding:0;background:#14AED0;color:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 3px 10px rgba(0,0,0,.15);transition:background .2s}
.lp-section .lp-arrow:focus,.lp-section .lp-arrow:active{background:#14AED0;color:#fff;outline:none}
.lp-section .lp-arrow:hover,.lp-section .lp-arrow:focus-visible{background:#0e8fab;color:#fff}
.lp-section button{-webkit-tap-highlight-color:transparent}
.lp-arrow svg{width:22px;height:22px}
.lp-count{text-align:center;margin-top:14px;font-size:1.05em;color:#555}
.lp-dots{display:flex;flex-wrap:wrap;justify-content:center;gap:8px;margin-top:10px}
.lp-section .lp-dot,.lp-section .lp-dot:hover,.lp-section .lp-dot:focus{width:11px;height:11px;min-height:0;border-radius:50%;border:0;padding:0;background:#c9d6dc;cursor:pointer;box-shadow:none}
.lp-section .lp-dot[aria-current="true"]{background:#14AED0;transform:scale(1.25)}
.lp-actions{display:flex;flex-wrap:wrap;justify-content:center;gap:12px;margin-top:22px}
.lp-btn{display:inline-flex;align-items:center;gap:8px;background:#14AED0;color:#fff!important;border:0;border-radius:30px;padding:11px 24px;font-size:1.05em;font-weight:600;font-family:inherit;line-height:1.2;cursor:pointer;text-decoration:none!important;transition:background .2s}
.lp-section .lp-btn:focus,.lp-section .lp-btn:active{background:#14AED0;color:#fff;outline:none}
.lp-section .lp-btn:hover,.lp-section .lp-btn:focus-visible{background:#0e8fab;color:#fff}
.lp-btn svg{width:20px;height:20px;flex:0 0 auto}
@media (max-width:767px){
.lp-section{padding:0 8px 40px}
.lp-carousel{gap:0;position:relative}
.lp-arrow{position:absolute;z-index:2;top:50%;margin-top:-18px;width:36px;height:36px;background:rgba(20,174,208,.85)}
.lp-arrow svg{width:18px;height:18px}
.lp-prev{right:2px}.lp-next{left:2px}
.lp-slide{height:auto;padding:12px}
.lp-slide img{max-height:78vh}
.lp-btn{padding:10px 18px}
}
</style>"""

ICON_PREV = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M8.6 5.4 15.2 12l-6.6 6.6 1.4 1.4 8-8-8-8z"/></svg>'
ICON_NEXT = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M15.4 5.4 8.8 12l6.6 6.6-1.4 1.4-8-8 8-8z"/></svg>'
ICON_DOWNLOAD = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M11 3h2v9.6l3.3-3.3 1.4 1.4L12 16.4l-5.7-5.7 1.4-1.4 3.3 3.3zM5 19h14v2H5z"/></svg>'
ICON_PRINT = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M7 3h10v4H7zM5 8h14a2 2 0 0 1 2 2v6h-4v4H7v-4H3v-6a2 2 0 0 1 2-2zm4 7v3h6v-3zm8-4.5a1 1 0 1 0 0 2 1 1 0 0 0 0-2z"/></svg>'
ICON_SHARE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M18 16a3 3 0 0 0-2.4 1.2l-6.7-3.4a3 3 0 0 0 0-1.6l6.7-3.4A3 3 0 1 0 15 7l-6.7 3.4a3 3 0 1 0 0 3.2L15 17a3 3 0 1 0 3-1z"/></svg>'

JS = r"""<script id="lp-js">
(function(){
var box=document.querySelector('.lp-carousel');if(!box){return;}
var track=box.querySelector('.lp-track'),slides=[].slice.call(track.querySelectorAll('.lp-slide'));
var dotsBox=document.querySelector('.lp-dots'),count=document.querySelector('.lp-count');
var dl=document.querySelector('.lp-download'),pr=document.querySelector('.lp-print'),sh=document.querySelector('.lp-share');
var cur=0,dots=[],shareFile=null;
function fit(){track.style.height=window.innerWidth<768?slides[cur].offsetHeight+'px':'';}
window.addEventListener('resize',fit);
slides.forEach(function(s,i){var b=document.createElement('button');b.type='button';b.className='lp-dot';b.setAttribute('aria-label','תמונה '+(i+1));b.addEventListener('click',function(){go(i);});dotsBox.appendChild(b);dots.push(b);});
function go(i,instant){i=(i+slides.length)%slides.length;var t=track.getBoundingClientRect(),r=slides[i].getBoundingClientRect(),d=r.left-t.left-(t.width-r.width)/2;if(instant){track.style.scrollBehavior='auto';track.scrollLeft+=d;track.style.scrollBehavior='';set(i);}else{track.scrollBy({left:d,behavior:'smooth'});set(i);}}
function set(i){cur=i;var s=slides[i];dots.forEach(function(d,j){d.setAttribute('aria-current',j===i?'true':'false');});
count.textContent=(i+1)+' מתוך '+slides.length;fit();dl.href=s.getAttribute('data-png');dl.setAttribute('download',s.getAttribute('data-name')+'.png');shareFile=null;}
function nearest(){var t=track.getBoundingClientRect(),c=t.left+t.width/2,best=0,bd=1e9;slides.forEach(function(s,i){var r=s.getBoundingClientRect(),d=Math.abs(r.left+r.width/2-c);if(d<bd){bd=d;best=i;}});return best;}
var tmr;track.addEventListener('scroll',function(){clearTimeout(tmr);tmr=setTimeout(function(){var n=nearest();if(n!==cur){set(n);}},150);},{passive:true});
box.querySelector('.lp-prev').addEventListener('click',function(){go(cur-1);});
box.querySelector('.lp-next').addEventListener('click',function(){go(cur+1);});
track.addEventListener('keydown',function(e){if(e.key==='ArrowLeft'){e.preventDefault();go(cur+1);}else if(e.key==='ArrowRight'){e.preventDefault();go(cur-1);}});
pr.addEventListener('click',function(){var s=slides[cur],w=window.open('','_blank');if(!w){window.open(s.getAttribute('data-png'),'_blank');return;}
w.document.write('<!DOCTYPE html><html dir="rtl"><head><meta charset="utf-8"><title>'+s.getAttribute('data-name')+'</title><style>@page{margin:10mm}html,body{margin:0;height:100%}body{display:flex;align-items:center;justify-content:center}img{max-width:100%;max-height:100vh}</style></head><body><img src="'+location.origin+s.getAttribute('data-png')+'" onload="setTimeout(function(){window.focus();window.print();},300)"></body></html>');w.document.close();});
function fileFor(s){if(!shareFile){shareFile=fetch(s.getAttribute('data-jpg')).then(function(r){return r.blob();}).then(function(b){return new File([b],s.getAttribute('data-name')+'.jpg',{type:'image/jpeg'});}).catch(function(){return null;});}return shareFile;}
sh.addEventListener('pointerdown',function(){if(navigator.canShare){fileFor(slides[cur]);}});
sh.addEventListener('click',function(){var s=slides[cur],url=location.origin+location.pathname+'#'+s.id,text=s.getAttribute('data-name')+' – התמונות של החיים';
function wa(){window.open('https://wa.me/?text='+encodeURIComponent(text+'\n'+url),'_blank','noopener');}
if(navigator.canShare){fileFor(s).then(function(f){if(f&&navigator.canShare({files:[f]})){return navigator.share({files:[f],title:text,text:text+'\n'+url});}
return navigator.share({title:text,text:text,url:url});}).catch(function(e){if(!e||e.name!=='AbortError'){wa();}});}
else if(navigator.share){navigator.share({title:text,text:text,url:url}).catch(function(e){if(!e||e.name!=='AbortError'){wa();}});}else{wa();}});
set(0);var m=location.hash.match(/^#lp-(\d+)$/);if(m){var n=parseInt(m[1],10)-1;if(n>0&&n<slides.length){var jump=function(){go(n,true);};if(document.readyState==='complete'){jump();}else{window.addEventListener('load',jump);}}}
})();
</script>"""


def content_html(d):
    intro = ''.join('<p>%s</p>' % esc(p) for p in d['intro'])
    pics = d['pictures']
    return f'''<div data-elementor-type="wp-post" data-elementor-id="459" class="elementor elementor-459" data-elementor-post-type="page">
<section class="elementor-section elementor-top-section elementor-element elementor-element-fa9c593 elementor-section-boxed elementor-section-height-default" data-id="fa9c593" data-element_type="section">
<div class="elementor-container elementor-column-gap-default"><div class="elementor-column elementor-col-100 elementor-top-column elementor-element elementor-element-15d27ea" data-id="15d27ea" data-element_type="column"><div class="elementor-widget-wrap elementor-element-populated">
<div class="elementor-element elementor-element-b57d802 elementor-widget elementor-widget-heading" data-id="b57d802" data-element_type="widget" data-widget_type="heading.default"><div class="elementor-widget-container"><h1 class="elementor-heading-title elementor-size-default">{esc(d["title"])}</h1></div></div>
</div></div></div></section>
<section class="elementor-section elementor-top-section elementor-element elementor-element-997324d elementor-section-boxed elementor-section-height-default" data-id="997324d" data-element_type="section">
<div class="elementor-container elementor-column-gap-default"><div class="elementor-column elementor-col-100 elementor-top-column elementor-element elementor-element-1cd2bba" data-id="1cd2bba" data-element_type="column"><div class="elementor-widget-wrap elementor-element-populated">
<div class="elementor-element elementor-element-d37a37a lp-intro elementor-widget elementor-widget-text-editor" data-id="d37a37a" data-element_type="widget" data-widget_type="text-editor.default"><div class="elementor-widget-container">{intro}</div></div>
</div></div></div></section>
<section class="lp-section" aria-label="{esc(d["title"])}">
<div class="lp-wrap">
<div class="lp-carousel" role="region" aria-roledescription="קרוסלה" aria-label="{esc(d["title"])}">
<button type="button" class="lp-arrow lp-prev" aria-label="התמונה הקודמת">{ICON_PREV}</button>
<div class="lp-track" tabindex="0">
{slides_html(pics)}
</div>
<button type="button" class="lp-arrow lp-next" aria-label="התמונה הבאה">{ICON_NEXT}</button>
</div>
<div class="lp-count" aria-live="polite">1 מתוך {len(pics)}</div>
<div class="lp-dots"></div>
<div class="lp-actions">
<a class="lp-btn lp-download" href="/assets/life-pictures/{pics[0]["file"]}.png" download="{esc(pics[0]["name"])}.png">{ICON_DOWNLOAD}<span>הורדה</span></a>
<button type="button" class="lp-btn lp-print">{ICON_PRINT}<span>הדפסה</span></button>
<button type="button" class="lp-btn lp-share">{ICON_SHARE}<span>שיתוף</span></button>
</div>
</div>
</section>
</div>
'''


def set_meta(t, attr, key, value):
    pat = re.compile(r'(<meta %s="%s" content=")[^"]*(")' % (attr, re.escape(key)))
    if pat.search(t):
        return pat.sub(lambda m: m.group(1) + value + m.group(2), t, count=1)
    return t.replace('</title>', '</title>\n<meta %s="%s" content="%s">' % (attr, key, value), 1)


def cmd_page():
    d = load()
    path = d['path']
    t = open(TEMPLATE, encoding='utf-8').read()
    # main content: replace the services page's own content block (header and footer stay)
    s = t.find('<div data-elementor-type="wp-post" data-elementor-id="459"')
    assert s > 0, 'services page layout changed'
    depth = 0
    for m in re.finditer(r'<div\b|</div>', t[s:]):
        depth += 1 if m.group(0) == '<div' else -1
        if depth == 0:
            e = s + m.end()
            break
    t = t[:s] + content_html(d) + t[e:]
    # head
    title = esc(d['title'])
    desc = esc(d['intro'][0])
    image = BASE + '/assets/life-pictures/%s.jpg' % d['pictures'][0]['file']
    t = re.sub(r'<title>.*?</title>', '<title>%s</title>' % title, t, count=1, flags=re.S)
    for attr, key, val in (('name', 'description', desc), ('property', 'og:title', title),
                           ('property', 'og:description', desc), ('name', 'twitter:title', title),
                           ('name', 'twitter:description', desc), ('name', 'twitter:card', 'summary_large_image'),
                           ('property', 'og:image', image), ('name', 'twitter:image', image)):
        t = set_meta(t, attr, key, val)
    t = t.replace('https://www.victory.org.il/my-services/"', BASE + path + '"')
    # links that point at this page itself (skip links, accessibility bar, cookie banner, contact form)
    for suffix in ('#content"', '#contact"', '#"'):
        t = t.replace('"/my-services/' + suffix, '"' + path + suffix)
    t = t.replace('name="page" value="/my-services/"', 'name="page" value="%s"' % path)
    # the menu must not mark the services page as the current one
    t = re.sub(r' current-menu-item| current_page_item', '', t)
    t = t.replace(' aria-current="page"', '').replace(' elementor-item-active', '')
    t = t.replace('</head>', CSS + '\n</head>', 1)
    t = t.replace('</body>', JS + '\n</body>', 1)
    out = os.path.join(ROOT, path.strip('/'), 'index.html')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(t)
    print('wrote', out, len(t))


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == 'images':
        cmd_images(sys.argv[2])
    elif len(sys.argv) >= 2 and sys.argv[1] == 'page':
        cmd_page()
    else:
        print(__doc__)
