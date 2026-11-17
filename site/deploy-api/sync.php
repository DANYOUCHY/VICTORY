<?php
// Called by GitHub (.github/workflows/live-update.yml) right after every update of main,
// so the live site takes the new version at once instead of waiting for the scheduled pull.
header('Content-Type: text/plain; charset=utf-8');
header('X-Robots-Tag: noindex');
// The key lives outside the repository, in a file the web server can read but visitors cannot.
// The same value is the GitHub repository secret VICTORY_SYNC_KEY. To rotate: write a new value
// to this file and update the secret; never put the key itself in the repository.
$keyFile = '/home/dhdanchi/victory-sync.key';
$key = is_readable($keyFile) ? trim((string) file_get_contents($keyFile)) : '';
if ($key === '') {
    http_response_code(500);
    exit('sync key is not configured');
}
if (!hash_equals($key, isset($_SERVER['HTTP_X_SYNC_KEY']) ? $_SERVER['HTTP_X_SYNC_KEY'] : '')) {
    http_response_code(403);
    exit('forbidden');
}
$disabled = array_map('trim', explode(',', (string) ini_get('disable_functions')));
if (!function_exists('exec') || in_array('exec', $disabled, true)) {
    http_response_code(500);
    exit('exec is disabled');
}
$script = '/home/dhdanchi/victory-static-sync.sh';
$lock = '/home/dhdanchi/victory-sync.lock';
$cmd = "if command -v flock >/dev/null 2>&1; then flock $lock /bin/bash $script; else /bin/bash $script; fi";
exec('nohup sh -c ' . escapeshellarg($cmd) . ' >/dev/null 2>&1 &');
echo 'ok';
