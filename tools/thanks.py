"""Create the site's two simple pages, built from the contact page so they keep the
site's header, footer and styles:
  site/thanks/index.html   shown after sending the contact form
  site/404.html            shown for an address that does not exist (same text WordPress showed)
"""
import os
import re
import sys

root = sys.argv[1] if len(sys.argv) > 1 else 'site'
base = open(os.path.join(root, 'connect', 'index.html'), encoding='utf-8').read()

BUTTON = ('display:inline-block;padding:12px 28px;margin:0 6px;border-radius:30px;'
          'background:#0f7c8c;color:#fff;text-decoration:none')

def page(title, h1, text, buttons, address):
    t = base
    s = t.index('<main id="main" class="site-main">')
    e = t.index('</main>', s)
    links = ''.join('<a href="%s" style="%s">%s</a>' % (href, BUTTON, label) for href, label in buttons)
    body = ('<main id="main" class="site-main">\n'
            '<div style="max-width:640px;margin:80px auto;padding:0 16px;text-align:center;direction:rtl">\n'
            '<h1 style="color:#0f7c8c;font-size:2.4em;margin-bottom:.4em">%s</h1>\n'
            '<p style="font-size:1.25em;line-height:1.7">%s</p>\n'
            '<p style="margin-top:2em">%s</p>\n</div>\n') % (h1, text, links)
    t = t[:s] + body + t[e:]
    t = re.sub(r'<title>.*?</title>', '<title>%s</title>' % title, t, count=1, flags=re.S)
    t = re.sub(r'<meta name=["\']robots["\'][^>]*>', '', t)
    t = t.replace('<head>', '<head>\n<meta name="robots" content="noindex">', 1)
    t = t.replace('https://www.victory.org.il/connect/', address)
    return t

os.makedirs(os.path.join(root, 'thanks'), exist_ok=True)
open(os.path.join(root, 'thanks', 'index.html'), 'w', encoding='utf-8').write(page(
    'תודה – שיטת מנצחים', 'תודה רבה!', 'ההודעה שלך התקבלה. אחזור אליך בהקדם.',
    [('/', 'חזרה לדף הבית')], 'https://www.victory.org.il/thanks/'))
open(os.path.join(root, '404.html'), 'w', encoding='utf-8').write(page(
    'הדף לא נמצא – כמו שאתה', 'דף זה אינו קיים.', 'נראה שהקישור שהוביל לכאן אינו תקין.',
    [('/', 'לדף הבית'), ('/blog/', 'לבלוג')], 'https://www.victory.org.il/'))
print('thanks and 404 pages written')
