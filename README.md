# VICTORY

האתר `victory.org.il` כאתר סטטי.

- `site/`: קבצי האתר שהשרת מגיש למבקרים.
- `site/assets/`: כל התמונות, העיצובים, הסקריפטים והגופנים של האתר. האתר לא משתמש בתיקיות של וורדפרס (`wp-content`, `wp-includes`).
- `tools/`: הכלים של האתר.
- `server/`: הגדרות השרת.
- `.github/workflows/youtube-feed.yml`: מעדכן את הסרטונים בסרגל הצד כל 6 שעות.
- `.github/workflows/rebuild.yml` ו־`compare.yml`: הפעלה ידנית בלבד, ורק כל עוד וורדפרס קיים.

## בדיקה שהאתר עומד בפני עצמו
- `python3 tools/audit_wp.py site`: מוצא קבצים חסרים וכל הפניה לוורדפרס.
- `python3 tools/simulate_no_wp.py site`: פותח כל דף במחשב ובטלפון כאילו וורדפרס נמחק, ומדווח מה נשבר.

## מחיקת וורדפרס
מה שחייב להישאר בשרת:
- התיקייה `static-repo` בתוך תיקיית האתר.
- בקובץ `.htaccess` של האתר: הקטע שבין `BEGIN StaticSite` לבין `END StaticSite`. את שאר הקטעים של וורדפרס ושל התוספים שלו אפשר למחוק.
- מחוץ לתיקיית האתר: הקובץ `victory-static-sync.sh`, התיקייה `victory-comments` ושתי המשימות המתוזמנות ב־cPanel (`server/cron.txt`).

כל השאר אפשר למחוק: קבצי וורדפרס (`wp-admin`, `wp-content`, `wp-includes`, קבצי `wp-*.php`, `index.php`) ומסד הנתונים שלו.
אחרי המחיקה צריך לכבות גם את המשימה המתוזמנת ״גיבוי לילי לוורדפרס״.

## חזרה לוורדפרס
בקובץ `.htaccess` של האתר בשרת, למחוק את הקטע שבין `BEGIN StaticSite` לבין `END StaticSite`.
