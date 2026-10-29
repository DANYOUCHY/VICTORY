"""Create site/thanks/, the page people see after sending the contact form.
Built from the contact page so it keeps the site's header, footer and styles."""
import os, re, sys
root = sys.argv[1] if len(sys.argv) > 1 else 'site'
t = open(os.path.join(root, 'connect', 'index.html'), encoding='utf-8').read()
s = t.index('<main id="main" class="site-main">'); e = t.index('</main>', s)
body = '''<main id="main" class="site-main">
<div style="max-width:640px;margin:80px auto;padding:0 16px;text-align:center;direction:rtl">
<h1 style="color:#0f7c8c;font-size:2.4em;margin-bottom:.4em">תודה רבה!</h1>
<p style="font-size:1.25em;line-height:1.7">ההודעה שלך התקבלה. אחזור אליך בהקדם.</p>
<p style="margin-top:2em"><a href="/" style="display:inline-block;padding:12px 28px;border-radius:30px;background:#0f7c8c;color:#fff;text-decoration:none">חזרה לדף הבית</a></p>
</div>
'''
t = t[:s] + body + t[e:]
t = re.sub(r'<title>.*?</title>', '<title>תודה – שיטת מנצחים</title>', t, flags=re.S)
t = re.sub(r'<meta name=["\']robots["\'][^>]*>', '', t)
t = t.replace('<head>', '<head>\n<meta name="robots" content="noindex">', 1)
t = t.replace('https://www.victory.org.il/connect/', 'https://www.victory.org.il/thanks/')
os.makedirs(os.path.join(root, 'thanks'), exist_ok=True)
open(os.path.join(root, 'thanks', 'index.html'), 'w', encoding='utf-8').write(t)
print('thanks page written')
