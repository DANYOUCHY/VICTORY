"""Comments on the static site.

  python3 tools/comments.py form                 point every comment form at /comments-api/submit.php
  python3 tools/comments.py publish approved.json  write approved comments into their posts

approved.json is a list of comments from the monthly digest, as the digest's DATA block
holds them: {"page": "/post-slug/", "name", "email", "url", "text", "time", "parent"}.
Published comments use the same markup WordPress produced, so they look the same.
"""
import datetime
import hashlib
import html
import json
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))
import posts as P  # noqa: E402

ROOT = P.ROOT

FORM_EXTRA = ('<input type="hidden" name="page" value="%s" />'
              '<input type="hidden" name="ts" value="" class="cmt-ts" />'
              '<span style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);clip-path:inset(50%%);white-space:nowrap" aria-hidden="true">'
              '<input type="text" name="website2" value="" tabindex="-1" autocomplete="off" /></span>')
SCRIPT = ('<script id="cmt-static">(function(){var f=document.getElementById("ast-commentform");if(!f)return;'
          'var t=f.querySelector(".cmt-ts");if(t)t.value=Date.now();'
          'var s=(location.search.match(/[?&]comment=(\\w+)/)||[])[1];if(!s)return;'
          'var m={pending:"תודה! התגובה התקבלה ותפורסם לאחר אישור.",missing:"נא למלא שם, אימייל ותגובה."};'
          'if(!m[s])return;var p=document.createElement("p");p.className="comment-notes";'
          'p.style.cssText="font-weight:600;padding:10px 14px;border-radius:6px;background:#e8f6f8;color:#0b5560";'
          'p.textContent=m[s];f.insertBefore(p,f.firstChild);'
          'var r=document.getElementById("respond");if(r)r.scrollIntoView();})();</script>')

def cmd_form():
    changed = 0
    for f in P.glob.glob(os.path.join(ROOT, '**', 'index.html'), recursive=True):
        t = open(f, encoding='utf-8').read()
        if 'id="ast-commentform"' not in t:
            continue
        o = t
        path = '/' + urllib.parse.quote(os.path.relpath(os.path.dirname(f), ROOT)) + '/'
        t = re.sub(r'(<form action=")[^"]*(" method="post" id="ast-commentform")', r'\1/comments-api/submit.php\2', t)
        if 'name="website2"' not in t:
            t = t.replace("<input type='hidden' name='comment_parent' id='comment_parent' value='0' />",
                          "<input type='hidden' name='comment_parent' id='comment_parent' value='0' />" + FORM_EXTRA % path, 1)
        if 'id="cmt-static"' not in t:
            t = t.replace('</body>', SCRIPT + '\n</body>', 1)
        if t != o:
            open(f, 'w', encoding='utf-8').write(t)
            changed += 1
    print('comment forms updated:', changed)

def avatar(email):
    h = hashlib.sha256(email.strip().lower().encode()).hexdigest()
    return ("<img alt='' src='https://secure.gravatar.com/avatar/%s?s=50&#038;d=mm&#038;r=g' "
            "srcset='https://secure.gravatar.com/avatar/%s?s=100&#038;d=mm&#038;r=g 2x' class='avatar avatar-50 photo' "
            "height='50' width='50' decoding='async' loading='lazy' />") % (h, h)

def comment_li(c, cid, page, post_id, depth):
    when = datetime.datetime.fromisoformat(c['time'])
    name = html.escape(c['name'], quote=False)
    if c.get('url', '').startswith(('http://', 'https://')):
        name = '<a href="%s" class="url" rel="ugc external nofollow">%s</a>' % (html.escape(c['url']), name)
    body = '<p>' + '</p>\n<p>'.join(html.escape(p, quote=False).replace('\n', '<br />\n')
                                    for p in re.split(r'\n\s*\n', c['text'].strip().replace('\r', ''))) + '</p>'
    reply_to = html.escape('להגיב ל' + c['name'])
    return (
        '<li class="comment even thread-even depth-%d" id="li-comment-%d">\n'
        '\t\t<article id="comment-%d" class="ast-comment">\n'
        "\t\t<div class= 'ast-comment-info'>\n"
        "\t\t\t<div class='ast-comment-avatar-wrap'>%s</div><!-- Remove 1px Space -->\n"
        '\t\t\t<div class="ast-comment-data-wrap"><div class="ast-comment-meta-wrap"><header class="ast-comment-meta ast-row ast-comment-author capitalize">'
        '<div class = "ast-comment-cite-wrap ast-col-lg-12"><cite><b class="fn">%s</b> </cite></div>'
        '<div class = "ast-comment-time ast-col-lg-12"><span class="timendate"><a href="%s#comment-%d">'
        '<time datetime="%s">%s</time></a></span></div> </div>\n'
        '\t\t\t\t</header> <!-- .ast-comment-meta -->\n\t\t\t</div>\n'
        '\t\t\t<section class="ast-comment-content comment">\n\t\t\t\t%s\n'
        '\t\t\t\t<div class="ast-comment-edit-reply-wrap">\n'
        '\t\t\t\t\t<span class="ast-reply-link"><a rel="nofollow" class="comment-reply-link" href="%s?replytocom=%d#respond" '
        'data-commentid="%d" data-postid="%d" data-belowelement="comment-%d" data-respondelement="respond" '
        'data-replyto="%s" aria-label="%s">תגובה</a></span>\t\t\t\t</div>\n'
        '\t\t\t</section> <!-- .ast-comment-content -->\n\t\t</div>\n'
        '\t\t</article><!-- #comment-## -->\n'
        '</li><!-- #comment-## -->\n'
    ) % (depth, cid, cid, avatar(c.get('email', '')), name, page, cid,
         when.isoformat(timespec='seconds'), when.strftime('%d/%m/%Y ב %H:%M'), body,
         page, cid, cid, post_id, cid, reply_to, reply_to)

def cmd_publish(spec):
    items = json.load(open(spec, encoding='utf-8'))
    by_page = {}
    for c in items:
        by_page.setdefault(c['page'], []).append(c)
    for page, cs in by_page.items():
        f = P.page_file(page)
        t = open(f, encoding='utf-8').read()
        post_id = int(re.search(r'\bpostid-(\d+)\b', t).group(1))
        title = html.unescape(re.search(r'<h1[^>]*>(.*?)</h1>', t, re.S).group(1)).strip()
        span = P.widget_spans(t, 'post-comments.theme_comments')[0]
        seg = t[span[0]:span[1]]
        for c in sorted(cs, key=lambda c: c['time']):
            cid = max([int(x) for x in re.findall(r'id="comment-(\d+)"', seg)] + [1000]) + 1
            li = comment_li(c, cid, page, post_id, 1)
            if '<ol class="ast-comment-list">' not in seg:
                seg = seg.replace('<div id="respond"', '<ol class="ast-comment-list">\n</ol><!-- .ast-comment-list -->\n<div id="respond"', 1)
            seg = seg.replace('</ol><!-- .ast-comment-list -->', li + '</ol><!-- .ast-comment-list -->', 1)
        n = len(re.findall(r'<li class="comment', seg))
        heading = '%s על &ldquo;%s&rdquo;' % ('1 מחשבה' if n == 1 else '%d מחשבות' % n, html.escape(title, quote=False))
        if '<h3 class="comments-title">' in seg:
            seg = re.sub(r'(<h3 class="comments-title">).*?(</h3>)', lambda m: m.group(1) + '\n\t\t\t' + heading + '\t\t' + m.group(2), seg, count=1, flags=re.S)
        else:
            seg = seg.replace('<ol class="ast-comment-list">',
                              '<div class="comments-count-wrapper">\n\t\t<h3 class="comments-title">\n\t\t\t%s\t\t</h3>\n\t</div>\n<ol class="ast-comment-list">' % heading, 1)
        t = t[:span[0]] + seg + t[span[1]:]
        open(f, 'w', encoding='utf-8').write(t)
        print('published %d on %s' % (len(cs), urllib.parse.unquote(page)))

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'form':
        cmd_form()
    elif len(sys.argv) > 2 and sys.argv[1] == 'publish':
        cmd_publish(sys.argv[2])
    else:
        sys.exit(__doc__)
