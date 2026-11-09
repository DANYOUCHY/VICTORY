<?php
// One-time: change the scheduled pull from every 10 minutes to once a day. Removed right after use.
header('Content-Type: text/plain; charset=utf-8');
if (!hash_equals('m1-oY8WDlEgP9pJWpX00wqSd37siNCC3nrumuJIIjjw', isset($_SERVER['HTTP_X_SYNC_KEY']) ? $_SERVER['HTTP_X_SYNC_KEY'] : '') || $_SERVER['REQUEST_METHOD'] !== 'POST') { http_response_code(403); exit('forbidden'); }
$cur = shell_exec('crontab -l 2>&1');
if (!is_string($cur) || $cur === '') { exit('could not read crontab'); }
$re = '#^\*/10 \* \* \* \*(\s+/bin/bash /home/dhdanchi/victory-static-sync\.sh)#m';
if (preg_match_all($re, $cur) !== 1) { exit('line not found exactly once: ' . preg_match_all('#victory-static-sync#', $cur)); }
file_put_contents('/home/dhdanchi/crontab-before-instant-update.txt', $cur);
$new = preg_replace($re, '23 4 * * *$1', $cur);
$tmp = tempnam('/home/dhdanchi', 'cron');
file_put_contents($tmp, $new);
$out = shell_exec('crontab ' . escapeshellarg($tmp) . ' 2>&1');
unlink($tmp);
$after = shell_exec('crontab -l 2>&1');
preg_match('#^.*victory-static-sync.*$#m', (string) $after, $m);
echo 'result: ' . trim((string) $out) . "\n" . ($m ? $m[0] : 'no line');
