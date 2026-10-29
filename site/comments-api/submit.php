<?php
// Receives comments from the posts on victory.org.il, drops spam, and keeps the rest
// for the monthly review. Nothing here is ever published automatically: approved
// comments are written into the post pages by tools/comments.py.

define('STORE', getenv('VICTORY_COMMENTS_STORE') ?: '/home/dhdanchi/victory-comments');   // outside the web root
const MAX_PER_HOUR = 5;                              // per visitor
const MAX_TEXT = 3000;

date_default_timezone_set('Asia/Jerusalem');
header('Cache-Control: no-store');
header('X-Robots-Tag: noindex');

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    http_response_code(405);
    exit;
}

function field($k) { return trim((string)($_POST[$k] ?? '')); }

// Where to send the visitor back to: only a path on this site.
$page = field('page');
if (!preg_match('#^/[^/\\\\][^\s]*$|^/$#u', $page) || strpos($page, '//') !== false) {
    $page = '/';
}
function back($page, $status) {
    header('Location: ' . strtok($page, '?#') . '?comment=' . $status . '#respond', true, 303);
    exit;
}

if (!is_dir(STORE)) {
    @mkdir(STORE, 0700, true);
    @file_put_contents(STORE . '/.htaccess', "Require all denied\n");
}

$name   = field('author');
$email  = field('email');
$url    = field('url');
$text   = field('comment');
$postId = (int)field('comment_post_ID');
$parent = (int)field('comment_parent');
$ts     = (int)field('ts');
$ip     = hash('sha256', ($_SERVER['REMOTE_ADDR'] ?? '') . '|victory-comments');

// Missing required fields: send the visitor back to fix them.
if ($name === '' || $text === '' || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    back($page, 'missing');
}

// ---- spam checks: a comment that fails any of these is dropped quietly ----
$spam = '';
$links = preg_match_all('#https?://|www\.#i', $text . ' ' . $name);
$hebrew = preg_match('/\p{Hebrew}/u', $text);
$age = (int)(microtime(true) * 1000) - $ts;

if (field('website2') !== '')                        $spam = 'honeypot';
elseif ($ts <= 0 || $age < 3000 || $age > 86400000)  $spam = 'timing';      // no script, or too fast
elseif (mb_strlen($text) > MAX_TEXT || mb_strlen($name) > 80) $spam = 'too long';
elseif ($links > 1)                                  $spam = 'links';
elseif ($links > 0 && !$hebrew)                      $spam = 'foreign link';
elseif (preg_match('#https?://#i', $name))           $spam = 'link in name';

// Rate limit and duplicates, per visitor.
$rateFile = STORE . '/rate.json';
$fh = fopen($rateFile, 'c+');
flock($fh, LOCK_EX);
$rate = json_decode(stream_get_contents($fh) ?: '{}', true) ?: [];
$now = time();
foreach ($rate as $k => $times) {
    $rate[$k] = array_values(array_filter($times, function ($t) use ($now) { return is_array($t) ? $t[0] > $now - 3600 : $t > $now - 3600; }));
    if (!$rate[$k]) unset($rate[$k]);
}
$mine = $rate[$ip] ?? [];
$hash = md5(mb_strtolower(preg_replace('/\s+/u', ' ', $text)));
if (!$spam && count($mine) >= MAX_PER_HOUR) $spam = 'rate';
if (!$spam) foreach ($mine as $t) { if (is_array($t) && $t[1] === $hash) { $spam = 'duplicate'; break; } }
$mine[] = [$now, $hash];
$rate[$ip] = $mine;
ftruncate($fh, 0); rewind($fh); fwrite($fh, json_encode($rate)); fflush($fh);
flock($fh, LOCK_UN); fclose($fh);

if ($spam) {
    file_put_contents(STORE . '/spam.log', date('c') . " $spam\n", FILE_APPEND | LOCK_EX);
    back($page, 'pending');   // a spammer learns nothing
}

$entry = [
    'id'      => bin2hex(random_bytes(6)),
    'time'    => date('c'),
    'page'    => strtok($page, '?#'),
    'post_id' => $postId,
    'parent'  => $parent,
    'name'    => $name,
    'email'   => $email,
    'url'     => $url,
    'text'    => $text,
];
file_put_contents(STORE . '/pending.jsonl', json_encode($entry, JSON_UNESCAPED_UNICODE) . "\n", FILE_APPEND | LOCK_EX);
back($page, 'pending');
