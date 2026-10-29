<?php
// Monthly comments digest for victory.org.il.
// Run by cron every Thursday at 07:00; it only acts on the first Thursday of the month.
// Sends ONE email with every comment waiting for review, then moves them to sent/.
// The review itself happens in a Claude scheduled task at 08:00 the same morning.
//
// cron: 0 7 * * 4  /usr/local/bin/php /home/dhdanchi/victory.org.il/static-repo/server/comments-digest.php

define('STORE', getenv('VICTORY_COMMENTS_STORE') ?: '/home/dhdanchi/victory-comments');
const TO = 'youchy0@gmail.com';
const FROM = 'comments@victory.org.il';

date_default_timezone_set('Asia/Jerusalem');
$force = in_array('--force', $argv ?? [], true);
if (!$force && !(date('N') === '4' && (int)date('j') <= 7)) {
    exit(0);   // not the first Thursday of the month
}

@mkdir(STORE . '/sent', 0700, true);
$pending = STORE . '/pending.jsonl';
$batch = STORE . '/sent/' . date('Y-m-d') . '.jsonl';

// Move the pending file aside first, so comments arriving now start a new month.
$items = [];
if (is_file($pending) && filesize($pending) > 0) {
    rename($pending, $batch . '.tmp');
    foreach (file($batch . '.tmp', FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
        $c = json_decode($line, true);
        if ($c) $items[] = $c;
    }
}
$spam = is_file(STORE . '/spam.log') ? count(file(STORE . '/spam.log')) : 0;

$lines = [];
$lines[] = 'תגובות שממתינות לאישור באתר victory.org.il';
$lines[] = 'מספר תגובות: ' . count($items) . '   |   ספאם שנחסם החודש: ' . $spam;
$lines[] = '';
foreach ($items as $i => $c) {
    $lines[] = sprintf('%d. %s  (%s)', $i + 1, $c['name'], $c['time']);
    $lines[] = '   פוסט: https://www.victory.org.il' . $c['page'];
    $lines[] = '   ' . str_replace("\n", "\n   ", $c['text']);
    $lines[] = '';
}
$lines[] = '----- DATA (for Claude) -----';
$lines[] = base64_encode(json_encode($items, JSON_UNESCAPED_UNICODE));
$lines[] = '----- END DATA -----';

$subject = '=?UTF-8?B?' . base64_encode('תגובות לאתר victory.org.il – ' . date('m/Y')) . '?=';
$headers = "From: " . FROM . "\r\nContent-Type: text/plain; charset=UTF-8\r\nContent-Transfer-Encoding: 8bit\r\nMIME-Version: 1.0";
$ok = getenv('VICTORY_COMMENTS_DRYRUN') ? (bool)file_put_contents(STORE . '/last-digest.txt', implode("\n", $lines))
                                        : mail(TO, $subject, implode("\n", $lines), $headers);

if ($ok) {
    if (is_file($batch . '.tmp')) rename($batch . '.tmp', $batch);
    @unlink(STORE . '/spam.log');
} elseif (is_file($batch . '.tmp')) {
    // mail failed: put the comments back so nothing is lost
    file_put_contents($pending, file_get_contents($batch . '.tmp'), FILE_APPEND | LOCK_EX);
    unlink($batch . '.tmp');
    exit(1);
}
