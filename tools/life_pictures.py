#!/usr/bin/env python3
"""The page "תמונות כח" (/power-pictures/; the old address /life-pictures/ forwards to it): two rows of insight pictures that keep moving
(in opposite directions). Clicking a picture opens it large, with buttons to download (in
the original quality), print and share it. The page is linked from the top menu and the
footer of every page.

The list of pictures is data/life-pictures.json. It mirrors the pictures (top level only)
of the owner's folder Downloads\\תמונות מנצחים על החיים. To update: change the entries
(file = a new life-NN number, never reused; src = the original's file name; name = short
name for the downloaded file; alt = the picture's text), then run:

  python3 tools/life_pictures.py images "<folder with the original images>"
  python3 tools/life_pictures.py page

The title, text and download explanation are in the same data file. After changing the
title, also run "python3 tools/life_pictures.py menu" (it updates the menu label on every
page; it also adds the menu links if they are missing).

"images" makes, for each picture, the original for download and print (.png, or .jpg
without its camera data), a .jpg for sharing and two .webp sizes for the page, in
site/assets/life-pictures/, and deletes files of pictures no longer in the list.
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
URL_DIR = '/assets/life-pictures/'
TEMPLATE = os.path.join(ROOT, 'my-services', 'index.html')
BASE = 'https://www.victory.org.il'


def load():
    with open(DATA, encoding='utf-8') as f:
        return json.load(f)


def is_jpeg(p):
    return os.path.splitext(p['src'])[1].lower() in ('.jpg', '.jpeg')


def original(p):
    return p['file'] + ('.jpg' if is_jpeg(p) else '.png')


def strip_jpeg_metadata(data):
    """Drop Exif/XMP (APP1) and comment blocks from a JPEG without re-compressing it."""
    out, i = bytearray(data[:2]), 2
    while i < len(data) - 1:
        if data[i] != 0xFF:
            break
        marker = data[i + 1]
        if marker == 0xDA:  # start of image data: copy the rest as is
            out += data[i:]
            return bytes(out)
        size = int.from_bytes(data[i + 2:i + 4], 'big')
        if marker not in (0xE1, 0xFE):
            out += data[i:i + 2 + size]
        i += 2 + size
    return data


def cmd_images(src_dir):
    from PIL import Image
    os.makedirs(OUT_DIR, exist_ok=True)
    wanted = set()
    for p in load()['pictures']:
        src = os.path.join(src_dir, p['src'])
        base = os.path.join(OUT_DIR, p['file'])
        im = Image.open(src).convert('RGB')
        if is_jpeg(p):
            with open(src, 'rb') as f:
                clean = strip_jpeg_metadata(f.read())
            with open(base + '.jpg', 'wb') as f:      # download, print and share
                f.write(clean)
        else:
            shutil.copyfile(src, base + '.png')       # download and print
            im.save(base + '.jpg', 'JPEG', quality=88, optimize=True, progressive=True)  # share
            wanted.add(p['file'] + '.png')
        wanted.add(p['file'] + '.jpg')
        for width in (600, 1100):
            copy = im.copy()
            if copy.width > width:
                copy = copy.resize((width, round(copy.height * width / copy.width)), Image.LANCZOS)
            copy.save('%s-%d.webp' % (base, width), 'WEBP', quality=82, method=6)
            wanted.add('%s-%d.webp' % (p['file'], width))
        print(p['file'], im.size)
    for name in os.listdir(OUT_DIR):
        if name not in wanted:
            os.remove(os.path.join(OUT_DIR, name))
            print('removed', name)


def esc(s):
    return html.escape(s, quote=True)


def items_html(pics, indexes):
    from PIL import Image
    out = []
    for i in indexes:
        p = pics[i]
        thumb = URL_DIR + p['file'] + '-600.webp'
        w, h = Image.open(os.path.join(OUT_DIR, p['file'] + '-600.webp')).size
        out.append(f'<a class="lp-item" href="{URL_DIR}{original(p)}" data-i="{i}" data-elementor-open-lightbox="no">'
                   f'<img src="{thumb}" width="{w}" height="{h}" alt="{esc(p["alt"])}" decoding="async"></a>')
    return ''.join(out)


CSS = """<style id="lp-css">
.lp-intro .elementor-widget-container{max-width:820px;margin:0 auto;text-align:right;font-size:20px;line-height:1.8}
.lp-intro p{margin:0 0 .9em}
.lp-intro p.lp-lead{text-align:center;font-size:24px;line-height:1.55;font-weight:600;color:#0e8fab;margin-bottom:1.1em}
.lp-howto{max-width:820px;margin:28px auto 0;background:#eef9fc;border-right:5px solid #14AED0;border-radius:12px;padding:20px 26px;text-align:right;line-height:1.7}
.lp-howto h2{margin:0 0 10px;font-size:24px;line-height:1.4;color:#0e8fab}
.lp-howto ol{margin:0;padding:0 1.3em 0 0}
.lp-howto li{margin:0 0 6px;font-size:18px}
.lp-quality{color:#cfe9f1;text-align:center;margin:10px 0 0;font-size:.98em}
.lp-section{padding:10px 0 50px;overflow:hidden}
.lp-rows{display:flex;flex-direction:column;gap:18px}
.lp-row{overflow:hidden;direction:ltr;-webkit-mask-image:linear-gradient(90deg,transparent,#000 5%,#000 95%,transparent);mask-image:linear-gradient(90deg,transparent,#000 5%,#000 95%,transparent)}
.lp-belt{display:flex;width:max-content;padding:10px 0;animation:lp-move var(--lp-dur,60s) linear infinite}
.lp-row-b .lp-belt{animation-direction:reverse}
.lp-row:hover .lp-belt,.lp-rows.lp-paused .lp-belt{animation-play-state:paused}
@keyframes lp-move{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.lp-item{flex:0 0 auto;display:block;height:300px;margin-right:18px;border-radius:12px;overflow:hidden;box-shadow:0 4px 14px rgba(0,0,0,.2);transition:transform .25s}
.lp-item:hover,.lp-item:focus-visible{transform:scale(1.04)}
.lp-item img{display:block;height:100%;width:auto;max-width:none;border-radius:0}
.lp-hint{text-align:center;margin:20px 15px 0;color:#555;font-size:1.05em}
html.lp-lock{overflow:hidden}
.lp-viewer{position:fixed;top:0;right:0;bottom:0;left:0;z-index:2147483000;background:rgba(8,12,16,.97);display:flex;flex-direction:column;padding:10px 12px 18px;box-sizing:border-box}
.lp-viewer[hidden]{display:none}
.lp-v-top{display:flex;justify-content:space-between;align-items:center;min-height:46px}
.lp-count{color:#fff;font-size:1.05em;padding:0 6px}
.lp-v-main{flex:1;min-height:0;display:flex;align-items:center;gap:14px}
.lp-stage{flex:1;min-width:0;height:100%;margin:0;display:flex;align-items:center;justify-content:center}
.lp-big{max-width:100%;max-height:100%;width:auto;height:auto;object-fit:contain;border-radius:6px;box-shadow:0 10px 34px rgba(0,0,0,.5)}
.lp-viewer button{-webkit-tap-highlight-color:transparent;font-family:inherit}
.lp-viewer .lp-close,.lp-viewer .lp-close:hover,.lp-viewer .lp-close:focus{width:44px;height:44px;min-height:0;border-radius:50%;border:0;padding:0;background:rgba(255,255,255,.14);color:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:none}
.lp-close svg{width:22px;height:22px}
.lp-viewer .lp-arrow,.lp-viewer .lp-arrow:focus,.lp-viewer .lp-arrow:active{flex:0 0 auto;width:50px;height:50px;min-height:0;border-radius:50%;border:0;padding:0;background:#14AED0;color:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 3px 10px rgba(0,0,0,.3);outline:none}
.lp-viewer .lp-arrow:hover,.lp-viewer .lp-arrow:focus-visible{background:#0e8fab;color:#fff}
.lp-arrow svg{width:24px;height:24px}
.lp-actions{display:flex;flex-wrap:wrap;justify-content:center;gap:12px;margin-top:16px}
.lp-viewer .lp-btn,.lp-viewer .lp-btn:focus,.lp-viewer .lp-btn:active{display:inline-flex;align-items:center;gap:8px;background:#14AED0;color:#fff!important;border:0;border-radius:30px;padding:11px 24px;font-size:1.05em;font-weight:600;line-height:1.2;cursor:pointer;text-decoration:none!important;outline:none}
.lp-viewer .lp-btn:hover,.lp-viewer .lp-btn:focus-visible{background:#0e8fab}
.lp-btn svg{width:20px;height:20px;flex:0 0 auto}
@media (max-width:767px){
.lp-rows{gap:10px}
.lp-item{height:190px;margin-right:12px;border-radius:10px}
.lp-viewer{padding:8px 6px 14px}
.lp-v-main{position:relative;gap:0}
.lp-viewer .lp-arrow,.lp-viewer .lp-arrow:focus,.lp-viewer .lp-arrow:active{position:absolute;z-index:2;top:50%;margin-top:-20px;width:40px;height:40px;background:rgba(20,174,208,.85)}
.lp-arrow svg{width:20px;height:20px}
.lp-viewer .lp-prev{right:2px}.lp-viewer .lp-next{left:2px}
.lp-viewer .lp-btn{padding:10px 18px}
.lp-intro .elementor-widget-container{font-size:17px;line-height:1.75}
.lp-intro p.lp-lead{font-size:20px}
.lp-howto h2{font-size:20px}
.lp-howto li{font-size:16px}
.lp-howto{margin:22px 4px 0;padding:16px 18px}
}
@media (prefers-reduced-motion:reduce){.lp-belt{animation:none}.lp-row{overflow-x:auto}}
</style>"""

ICON_PREV = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M8.6 5.4 15.2 12l-6.6 6.6 1.4 1.4 8-8-8-8z"/></svg>'
ICON_NEXT = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M15.4 5.4 8.8 12l6.6 6.6-1.4 1.4-8-8 8-8z"/></svg>'
ICON_CLOSE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M18.3 5.7 12 12l6.3 6.3-1.4 1.4L10.6 13.4 4.3 19.7 2.9 18.3 9.2 12 2.9 5.7 4.3 4.3l6.3 6.3 6.3-6.3z" transform="translate(1 0)"/></svg>'
ICON_DOWNLOAD = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M11 3h2v9.6l3.3-3.3 1.4 1.4L12 16.4l-5.7-5.7 1.4-1.4 3.3 3.3zM5 19h14v2H5z"/></svg>'
ICON_PRINT = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M7 3h10v4H7zM5 8h14a2 2 0 0 1 2 2v6h-4v4H7v-4H3v-6a2 2 0 0 1 2-2zm4 7v3h6v-3zm8-4.5a1 1 0 1 0 0 2 1 1 0 0 0 0-2z"/></svg>'
ICON_SHARE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M18 16a3 3 0 0 0-2.4 1.2l-6.7-3.4a3 3 0 0 0 0-1.6l6.7-3.4A3 3 0 1 0 15 7l-6.7 3.4a3 3 0 1 0 0 3.2L15 17a3 3 0 1 0 3-1z"/></svg>'

JS = r"""<script id="lp-js">
(function(){
var dataEl=document.getElementById('lp-data');if(!dataEl){return;}
var data=JSON.parse(dataEl.textContent),wrap=document.querySelector('.lp-rows'),rows=[].slice.call(document.querySelectorAll('.lp-row'));
var reduce=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
function copy(n){var c=n.cloneNode(true);c.setAttribute('aria-hidden','true');c.setAttribute('tabindex','-1');return c;}
var lastW=0;
function fill(){if(window.innerWidth===lastW){return;}lastW=window.innerWidth;
rows.forEach(function(row){var belt=row.querySelector('.lp-belt');if(!belt._orig){belt._orig=[].slice.call(belt.children);}
while(belt.children.length>belt._orig.length){belt.removeChild(belt.lastChild);}
if(reduce){return;}
var one=belt.scrollWidth,w=one;while(w<row.clientWidth+40){belt._orig.forEach(function(n){belt.appendChild(copy(n));});w+=one;}
[].slice.call(belt.children).forEach(function(n){belt.appendChild(copy(n));});
belt.style.setProperty('--lp-dur',Math.max(20,Math.round(w/(window.innerWidth<768?28:38)))+'s');});}
fill();window.addEventListener('resize',function(){clearTimeout(fill.t);fill.t=setTimeout(fill,200);});
var held;wrap.addEventListener('touchstart',function(){clearTimeout(held);wrap.classList.add('lp-paused');},{passive:true});
wrap.addEventListener('touchend',function(){held=setTimeout(function(){if(v.hidden){wrap.classList.remove('lp-paused');}},1500);},{passive:true});
var v=document.getElementById('lp-viewer');document.body.appendChild(v);
var big=v.querySelector('.lp-big'),cnt=v.querySelector('.lp-count'),dl=v.querySelector('.lp-download'),cur=0,from=null,shareFile=null;
function show(i){cur=(i+data.length)%data.length;var p=data[cur];big.src=p.b;big.alt=p.a;cnt.textContent=(cur+1)+' מתוך '+data.length;
dl.href=p.o;dl.setAttribute('download',p.n+p.o.slice(p.o.lastIndexOf('.')));shareFile=null;
try{history.replaceState(null,'','#lp-'+(cur+1));}catch(e){}
[1,-1].forEach(function(d){(new Image()).src=data[(cur+d+data.length)%data.length].b;});}
function open(i,el){from=el||null;v.hidden=false;document.documentElement.classList.add('lp-lock');wrap.classList.add('lp-paused');show(i);v.querySelector('.lp-close').focus();}
function close(){v.hidden=true;document.documentElement.classList.remove('lp-lock');wrap.classList.remove('lp-paused');
try{history.replaceState(null,'',location.pathname+location.search);}catch(e){}if(from){from.focus();}}
document.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('.lp-item');if(a){e.preventDefault();open(parseInt(a.getAttribute('data-i'),10),a);}});
v.querySelector('.lp-close').addEventListener('click',close);
v.querySelector('.lp-prev').addEventListener('click',function(){show(cur-1);});
v.querySelector('.lp-next').addEventListener('click',function(){show(cur+1);});
v.addEventListener('click',function(e){if(e.target===v||e.target.classList.contains('lp-stage')||e.target.classList.contains('lp-v-main')){close();}});
document.addEventListener('keydown',function(e){if(v.hidden){return;}if(e.key==='Escape'){close();}else if(e.key==='ArrowLeft'){show(cur+1);}else if(e.key==='ArrowRight'){show(cur-1);}});
var sx=null;v.addEventListener('touchstart',function(e){sx=e.touches.length===1?e.touches[0].clientX:null;},{passive:true});
v.addEventListener('touchend',function(e){if(sx===null){return;}var dx=e.changedTouches[0].clientX-sx;sx=null;if(Math.abs(dx)>45){show(dx>0?cur+1:cur-1);}},{passive:true});
v.querySelector('.lp-print').addEventListener('click',function(){var p=data[cur],w=window.open('','_blank');if(!w){window.open(p.o,'_blank');return;}
w.document.write('<!DOCTYPE html><html dir="rtl"><head><meta charset="utf-8"><title>'+p.n+'</title><style>@page{margin:10mm}html,body{margin:0;height:100%}body{display:flex;align-items:center;justify-content:center}img{max-width:100%;max-height:100vh}</style></head><body><img src="'+location.origin+p.o+'" onload="setTimeout(function(){window.focus();window.print();},300)"></body></html>');w.document.close();});
var sh=v.querySelector('.lp-share');
function fileFor(p){if(!shareFile){shareFile=fetch(p.s).then(function(r){return r.blob();}).then(function(b){return new File([b],p.n+'.jpg',{type:'image/jpeg'});}).catch(function(){return null;});}return shareFile;}
sh.addEventListener('pointerdown',function(){if(navigator.canShare){fileFor(data[cur]);}});
sh.addEventListener('click',function(){var p=data[cur],url=location.origin+location.pathname+'#lp-'+(cur+1),text=p.n+' – '+document.querySelector('.lp-section').getAttribute('aria-label');
function wa(){window.open('https://wa.me/?text='+encodeURIComponent(text+'\n'+url),'_blank','noopener');}
if(navigator.canShare){fileFor(p).then(function(f){if(f&&navigator.canShare({files:[f]})){return navigator.share({files:[f],title:text,text:text+'\n'+url});}
return navigator.share({title:text,text:text,url:url});}).catch(function(e){if(!e||e.name!=='AbortError'){wa();}});}
else if(navigator.share){navigator.share({title:text,text:text,url:url}).catch(function(e){if(!e||e.name!=='AbortError'){wa();}});}else{wa();}});
var m=location.hash.match(/^#lp-(\d+)$/);if(m){var n=parseInt(m[1],10)-1;if(n>=0&&n<data.length){open(n);}}
})();
</script>"""


def content_html(d):
    intro = ''.join('<p%s>%s</p>' % (' class="lp-lead"' if n == 0 else '', esc(p)) for n, p in enumerate(d['intro']))
    how = d.get('howto')
    if how:
        intro += '<div class="lp-howto"><h2>%s</h2><ol>%s</ol></div>' % (
            esc(how['title']), ''.join('<li>%s</li>' % esc(x) for x in how['steps']))
    pics = d['pictures']
    title = esc(d['title'])
    data = [{'o': URL_DIR + original(p), 's': URL_DIR + p['file'] + '.jpg',
             'b': URL_DIR + p['file'] + '-1100.webp', 'n': p['name'], 'a': p['alt']} for p in pics]
    data_json = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    row_a = items_html(pics, range(0, len(pics), 2))
    row_b = items_html(pics, range(1, len(pics), 2))
    return f'''<div data-elementor-type="wp-post" data-elementor-id="459" class="elementor elementor-459" data-elementor-post-type="page">
<section class="elementor-section elementor-top-section elementor-element elementor-element-fa9c593 elementor-section-boxed elementor-section-height-default" data-id="fa9c593" data-element_type="section">
<div class="elementor-container elementor-column-gap-default"><div class="elementor-column elementor-col-100 elementor-top-column elementor-element elementor-element-15d27ea" data-id="15d27ea" data-element_type="column"><div class="elementor-widget-wrap elementor-element-populated">
<div class="elementor-element elementor-element-b57d802 elementor-widget elementor-widget-heading" data-id="b57d802" data-element_type="widget" data-widget_type="heading.default"><div class="elementor-widget-container"><h1 class="elementor-heading-title elementor-size-default">{title}</h1></div></div>
</div></div></div></section>
<section class="elementor-section elementor-top-section elementor-element elementor-element-997324d elementor-section-boxed elementor-section-height-default" data-id="997324d" data-element_type="section">
<div class="elementor-container elementor-column-gap-default"><div class="elementor-column elementor-col-100 elementor-top-column elementor-element elementor-element-1cd2bba" data-id="1cd2bba" data-element_type="column"><div class="elementor-widget-wrap elementor-element-populated">
<div class="elementor-element elementor-element-d37a37a lp-intro elementor-widget elementor-widget-text-editor" data-id="d37a37a" data-element_type="widget" data-widget_type="text-editor.default"><div class="elementor-widget-container">{intro}</div></div>
</div></div></div></section>
<section class="lp-section" aria-label="{title}">
<div class="lp-rows">
<div class="lp-row lp-row-a"><div class="lp-belt">{row_a}</div></div>
<div class="lp-row lp-row-b"><div class="lp-belt">{row_b}</div></div>
</div>
<p class="lp-hint">לחצו על תמונה כדי להגדיל אותה, להוריד, להדפיס או לשתף.</p>
</section>
<div class="lp-viewer" id="lp-viewer" role="dialog" aria-modal="true" aria-label="{title}" hidden>
<div class="lp-v-top"><span class="lp-count" aria-live="polite"></span><button type="button" class="lp-close" aria-label="סגירה">{ICON_CLOSE}</button></div>
<div class="lp-v-main">
<button type="button" class="lp-arrow lp-prev" aria-label="התמונה הקודמת">{ICON_PREV}</button>
<figure class="lp-stage"><img class="lp-big" src="" alt=""></figure>
<button type="button" class="lp-arrow lp-next" aria-label="התמונה הבאה">{ICON_NEXT}</button>
</div>
<div class="lp-actions">
<a class="lp-btn lp-download" href="{URL_DIR}{original(pics[0])}" download data-elementor-open-lightbox="no">{ICON_DOWNLOAD}<span>הורדה</span></a>
<button type="button" class="lp-btn lp-print">{ICON_PRINT}<span>הדפסה</span></button>
<button type="button" class="lp-btn lp-share">{ICON_SHARE}<span>שיתוף</span></button>
</div>
<p class="lp-quality">{esc(d.get('howto', {}).get('quality', ''))}</p>
</div>
<script type="application/json" id="lp-data">{data_json}</script>
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
    image = BASE + URL_DIR + '%s.jpg' % d['pictures'][0]['file']
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
    t = t.replace('menu-item-power-pictures"><a href="%s" class="elementor-item menu-link"' % path,
                  'menu-item-power-pictures current-menu-item"><a href="%s" aria-current="page" class="elementor-item elementor-item-active menu-link"' % path)
    t = t.replace('</head>', CSS + '\n</head>', 1)
    t = t.replace('</body>', JS + '\n</body>', 1)
    out = os.path.join(ROOT, path.strip('/'), 'index.html')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(t)
    print('wrote', out, len(t))


MENU_LI = ('<li class="menu-item menu-item-type-custom menu-item-object-custom menu-item-power-pictures">'
           '<a href="{path}" class="elementor-item menu-link"{tab}>{label}</a></li>')
BLOG_LI = re.compile(r'<li class="[^"]*menu-item-488[^"]*"><a href="/blog/"[^>]*>בלוג</a></li>')
OUR_LI = re.compile(r'(menu-item-power-pictures[^"]*"><a href="[^"]*"[^>]*>)[^<]*(</a>)')
FOOT_AFTER = '<li><a href="/blog/#sy-blog-articles">סרטונים ומאמרים</a></li>'


def cmd_menu():
    """Link the page from the top menu (after "בלוג") and the footer column "כלים לחיים"."""
    d = load()
    path, label = d['path'], esc(d.get('menu_label', d['title']))
    foot_li = '<li><a href="%s" class="sy-power-pictures">%s</a></li>' % (path, label)
    changed = 0
    for dirpath, _, files in os.walk(ROOT):
        if dirpath.startswith(os.path.join(ROOT, 'assets')):
            continue
        for name in files:
            if not name.endswith('.html'):
                continue
            f = os.path.join(dirpath, name)
            t = open(f, encoding='utf-8').read()
            if 'id="forward-page"' in t:
                continue
            new = t
            if 'menu-item-power-pictures' in new:
                new = OUR_LI.sub(lambda m: m.group(1) + label + m.group(2), new)
                new = re.sub(r'(menu-item-power-pictures[^"]*"><a href=")[^"]*', lambda m: m.group(1) + path, new)
            else:
                new = BLOG_LI.sub(lambda m: m.group(0) + '\n' + MENU_LI.format(
                    path=path, label=label, tab=' tabindex="-1"' if 'tabindex="-1"' in m.group(0) else ''), new)
            if 'sy-power-pictures' in new:
                new = re.sub(r'(class="sy-power-pictures">)[^<]*(</a>)', lambda m: m.group(1) + label + m.group(2), new)
                new = re.sub(r'<a href="[^"]*" class="sy-power-pictures">', '<a href="%s" class="sy-power-pictures">' % path, new)
            elif FOOT_AFTER in new:
                new = new.replace(FOOT_AFTER, FOOT_AFTER + foot_li)
            if new != t:
                with open(f, 'w', encoding='utf-8') as out:
                    out.write(new)
                changed += 1
    print('pages updated:', changed)


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == 'images':
        cmd_images(sys.argv[2])
    elif len(sys.argv) >= 2 and sys.argv[1] == 'page':
        cmd_page()
    elif len(sys.argv) >= 2 and sys.argv[1] == 'menu':
        cmd_menu()
    else:
        print(__doc__)
