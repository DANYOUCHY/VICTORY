# VICTORY

האתר `victory.org.il` כאתר סטטי.

- `site/`: קבצי האתר שהשרת מגיש למבקרים.
- `tools/`: הכלים שבונים את `site/` מתוך וורדפרס.
- `server/`: הגדרות השרת.
- `.github/workflows/rebuild.yml`: בונה את האתר מחדש מוורדפרס כל 3 שעות.
- `.github/workflows/youtube-feed.yml`: מעדכן את הסרטונים בסרגל הצד כל 6 שעות.

## חזרה לוורדפרס
בקובץ `.htaccess` של האתר בשרת, למחוק את הקטע שבין `BEGIN StaticSite` לבין `END StaticSite`.
