"""Point the Elementor contact forms at the site's own handler, /contact-api/send.php,
which emails each message from the server itself (no outside service).

Elementor's own script would try to send the form to WordPress, so the widget is
renamed to keep that script away while its look stays the same.
Works on a fresh copy from WordPress and on pages already converted earlier.
Safe to run more than once.
"""
import glob
import os
import re
import sys
import urllib.parse

root = sys.argv[1] if len(sys.argv) > 1 else 'site'
ACTION = '/contact-api/send.php'

FIELD_NAMES = {
    'form_fields[name]': 'שם',
    'form_fields[email]': 'email',
    'form_fields[0a1361c]': 'טלפון',
    'form_fields[747f061]': 'הודעה',
    'form_fields[honeypot]': '_honey',
}
HIDDEN = ('<input type="hidden" name="page" value="%s">'
          '<input type="hidden" name="ts" value="" class="ct-ts">'
          '<span style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);'
          'clip-path:inset(50%%);white-space:nowrap" aria-hidden="true">'
          '<input type="text" name="website2" value="" tabindex="-1" autocomplete="off"></span>')
SCRIPT = ('<script id="ct-static">(function(){var n=Date.now();'
          'document.querySelectorAll("form.elementor-form .ct-ts").forEach(function(i){i.value=n;});'
          'if(/[?&]contact=missing/.test(location.search))alert("נא למלא שם ואימייל תקין.");})();</script>')

FORM = re.compile(r'<form class="elementor-form" method="post"([^>]*)>(.*?)</form>', re.S)

def fix(page):
    def inner(m):
        attrs = re.sub(r'\s(?:action|accept-charset)="[^"]*"', '', m.group(1))
        body = m.group(2)
        body = re.sub(r'<input type="hidden" name="(?:post_id|form_id|referer_title|queried_id|_subject|_template|_next)"[^>]*>\s*', '', body)
        body = re.sub(r'<input type="hidden" name="page"[^>]*>|<input type="hidden" name="ts"[^>]*>'
                      r'|<span style="position:absolute;width:1px[^>]*><input type="text" name="website2"[^>]*></span>', '', body)
        for old, new in FIELD_NAMES.items():
            body = body.replace('name="%s"' % old, 'name="%s"' % new)
        return ('<form class="elementor-form" method="post" action="%s" accept-charset="UTF-8"%s>%s%s</form>'
                % (ACTION, attrs, HIDDEN % page, body))
    return inner

changed = 0
for f in glob.glob(os.path.join(root, '**', '*.html'), recursive=True):
    t = open(f, encoding='utf-8').read()
    if 'elementor-form' not in t:
        continue
    o = t
    rel = os.path.relpath(os.path.dirname(f), root)
    page = '/' if rel == '.' else '/' + urllib.parse.quote(rel) + '/'
    t = FORM.sub(fix(page), t)
    # keep Elementor's form script from taking over the submit
    t = t.replace('data-widget_type="form.default"', 'data-widget_type="form.static"')
    if 'id="ct-static"' not in t:
        t = t.replace('</body>', SCRIPT + '\n</body>', 1)
    if t != o:
        open(f, 'w', encoding='utf-8').write(t)
        changed += 1
print('pages with forms updated:', changed)
