<?php
// Brings changes from GitHub to the live site right away, instead of waiting for the
// 10-minute cron. Called after every push (GitHub webhook, or Claude after a change).
// It can only pull the site's own public repository, so it needs no password; it runs
// at most once every 15 seconds.

const SYNC = '/home/dhdanchi/victory-static-sync.sh';
const STAMP = '/home/dhdanchi/victory-comments/deploy-last';
const LOG = '/home/dhdanchi/victory-static-sync.log';

header('Cache-Control: no-store');
header('X-Robots-Tag: noindex');
header('Content-Type: text/plain; charset=UTF-8');
ignore_user_abort(true);
set_time_limit(120);

if (!is_dir(dirname(STAMP))) @mkdir(dirname(STAMP), 0700, true);
$fh = fopen(STAMP, 'c+');
if (!$fh || !flock($fh, LOCK_EX | LOCK_NB)) { echo "busy\n"; exit; }
$last = (int)stream_get_contents($fh);
if (time() - $last < 15) { echo "too soon\n"; exit; }
ftruncate($fh, 0); rewind($fh); fwrite($fh, (string)time()); fflush($fh);

$out = null;
if (function_exists('exec')) {
    exec('/bin/bash ' . escapeshellarg(SYNC) . ' 2>&1', $lines, $code);
    $out = $code === 0 ? 'ok' : 'failed ' . $code;
} elseif (function_exists('shell_exec')) {
    shell_exec('/bin/bash ' . escapeshellarg(SYNC) . ' 2>&1');
    $out = 'ok';
} else {
    $out = 'exec disabled';
}
flock($fh, LOCK_UN); fclose($fh);

$tail = @file(LOG, FILE_IGNORE_NEW_LINES) ?: [];
echo $out, "\n", end($tail) ?: '', "\n";
