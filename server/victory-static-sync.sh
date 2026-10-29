#!/bin/bash
# Keeps the static copy of victory.org.il in sync with GitHub (DANYOUCHY/VICTORY).
# Placed at /home/dhdanchi/victory-static-sync.sh and run by cron every 10 minutes.
REPO=/home/dhdanchi/victory.org.il/static-repo
LOG=/home/dhdanchi/victory-static-sync.log
GIT=$(command -v git || echo /usr/local/cpanel/3rdparty/bin/git)
if [ ! -d "$REPO/.git" ]; then
  rm -rf "$REPO.tmp"
  "$GIT" clone -q --depth 1 https://github.com/DANYOUCHY/VICTORY.git "$REPO.tmp" >>"$LOG" 2>&1 && mv "$REPO.tmp" "$REPO"
else
  cd "$REPO" || exit 1
  "$GIT" fetch -q --depth 1 origin main >>"$LOG" 2>&1 && "$GIT" reset -q --hard FETCH_HEAD >>"$LOG" 2>&1
  [ "$(ls .git/objects/pack 2>/dev/null | wc -l)" -gt 20 ] && "$GIT" gc -q --prune=now >>"$LOG" 2>&1
fi
chmod 755 "$REPO"   # the web server must be able to read the site
echo "$(date '+%F %T') $("$GIT" -C "$REPO" rev-parse --short HEAD 2>/dev/null)" >> "$LOG"
tail -n 300 "$LOG" > "$LOG.t" && mv "$LOG.t" "$LOG"
