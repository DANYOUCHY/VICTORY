"""Point the Elementor contact forms at FormSubmit, which emails each submission.

Elementor's own script would try to send the form to WordPress, so the widget is
renamed to keep that script away while its look stays the same.
Safe to run more than once.
"""
import glob
import os
import re
import sys

root = sys.argv[1] if len(sys.argv) > 1 else 'site'
TO = 'youchy0@gmail.com'
ACTION = 'https://formsubmit.co/' + TO

FIELD_NAMES = {
    'form_fields[name]': 'שם',
    'form_fields[email]': 'email',
    'form_fields[0a1361c]': 'טלפון',
    'form_fields[747f061]': 'הודעה',
    'form_fields[honeypot]': '_honey',
}
HIDDEN = (
    '<input type="hidden" name="_subject" value="פנייה חדשה מהאתר victory.org.il">'
    '<input type="hidden" name="_template" value="table">'
    '<input type="hidden" name="_next" value="https://www.victory.org.il/thanks/">'
)

FORM = re.compile(r'<form class="elementor-form" method="post"([^>]*)>(.*?)</form>', re.S)

def fix(m):
    body = m.group(2)
    body = re.sub(r'<input type="hidden" name="(?:post_id|form_id|referer_title|queried_id)"[^>]*>\s*', '', body)
    for old, new in FIELD_NAMES.items():
        body = body.replace('name="%s"' % old, 'name="%s"' % new)
    return ('<form class="elementor-form" method="post" action="%s" accept-charset="UTF-8"%s>%s%s</form>'
            % (ACTION, m.group(1), HIDDEN, body))

changed = 0
for f in glob.glob(os.path.join(root, '**', '*.html'), recursive=True):
    t = open(f, encoding='utf-8').read()
    if 'elementor-form' not in t:
        continue
    o = t
    if 'formsubmit.co' not in t:
        t = FORM.sub(fix, t)
    # keep Elementor's form script from taking over the submit
    t = t.replace('data-widget_type="form.default"', 'data-widget_type="form.static"')
    if t != o:
        open(f, 'w', encoding='utf-8').write(t)
        changed += 1
print('pages with forms updated:', changed)
