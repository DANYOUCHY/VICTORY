<?php
// Contact form for victory.org.il. Runs on the site's own server, no outside service:
// each message goes straight to the owner's mailbox. Spam is dropped quietly.

define('STORE', getenv('VICTORY_COMMENTS_STORE') ?: '/home/dhdanchi/victory-comments');   // outside the web root
const TO = 'youchy0@gmail.com';
const FROM = 'contact@victory.org.il';
const MAX_PER_HOUR = 5;

date_default_timezone_set('Asia/Jerusalem');
header('Cache-Control: no-store');
header('X-Robots-Tag: noindex');

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    http_response_code(405);
    exit;
}

function field($k) { return trim((string)($_POST[$k] ?? '')); }
function go($url) { header('Location: ' . $url, true, 303); exit; }

$page = field('page');
if (!preg_match('#^/[^\s]*$#u', $page) || strpos($page, '//') !== false) $page = '/';
$page = strtok($page, '?#');

$name  = field('שם');
$email = field('email');
$phone = field('טלפון');
$text  = field('הודעה');
$ts    = (int)field('ts');

if ($name === '' || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    go($page . '?contact=missing');
}

// ---- spam checks: failing any of these drops the message quietly ----
$spam = '';
$links = preg_match_all('#https?://|www\.#i', $text . ' ' . $name);
$age = (int)(microtime(true) * 1000) - $ts;
if (field('website2') !== '' || field('_honey') !== '') $spam = 'honeypot';
elseif ($ts <= 0 || $age < 3000 || $age > 86400000)  $spam = 'timing';
elseif (mb_strlen($text) > 5000 || mb_strlen($name) > 80) $spam = 'too long';
elseif ($links > 1)                                  $spam = 'links';
elseif ($links > 0 && !preg_match('/\p{Hebrew}/u', $text)) $spam = 'foreign link';
elseif (preg_match('#https?://#i', $name))           $spam = 'link in name';

if (!is_dir(STORE)) @mkdir(STORE, 0700, true);
$ip = hash('sha256', ($_SERVER['REMOTE_ADDR'] ?? '') . '|victory-contact');
$rateFile = STORE . '/contact-rate.json';
$fh = fopen($rateFile, 'c+');
flock($fh, LOCK_EX);
$rate = json_decode(stream_get_contents($fh) ?: '{}', true) ?: [];
$now = time();
foreach ($rate as $k => $times) {
    $rate[$k] = array_values(array_filter($times, function ($t) use ($now) { return $t > $now - 3600; }));
    if (!$rate[$k]) unset($rate[$k]);
}
if (!$spam && count($rate[$ip] ?? []) >= MAX_PER_HOUR) $spam = 'rate';
$rate[$ip][] = $now;
ftruncate($fh, 0); rewind($fh); fwrite($fh, json_encode($rate)); fflush($fh);
flock($fh, LOCK_UN); fclose($fh);

if ($spam) {
    file_put_contents(STORE . '/contact-spam.log', date('c') . " $spam\n", FILE_APPEND | LOCK_EX);
    go('/thanks/');   // a spammer learns nothing
}

$clean = function ($s) { return str_replace(["\r", "\n"], ' ', $s); };
$body = "פנייה חדשה מהאתר victory.org.il\n\n"
      . "שם: $name\n"
      . "אימייל: $email\n"
      . "טלפון: " . ($phone !== '' ? $phone : '-') . "\n"
      . "נשלח מהעמוד: https://www.victory.org.il$page\n"
      . "זמן: " . date('d/m/Y H:i') . "\n\n"
      . "ההודעה:\n" . ($text !== '' ? $text : '-') . "\n";
$subject = '=?UTF-8?B?' . base64_encode('פנייה חדשה מהאתר victory.org.il – ' . $clean($name)) . '?=';
$headers = "From: " . FROM . "\r\n"
         . "Reply-To: " . $clean($email) . "\r\n"
         . "Content-Type: text/plain; charset=UTF-8\r\nContent-Transfer-Encoding: 8bit\r\nMIME-Version: 1.0";

if (getenv('VICTORY_COMMENTS_DRYRUN')) {
    file_put_contents(STORE . '/last-contact.txt', $body);
    $ok = true;
} else {
    $ok = mail(TO, $subject, $body, $headers);
}
if (!$ok) {
    // keep it so nothing is lost, then still thank the visitor
    file_put_contents(STORE . '/contact-unsent.jsonl', json_encode(['time' => date('c'), 'name' => $name, 'email' => $email, 'phone' => $phone, 'page' => $page, 'text' => $text], JSON_UNESCAPED_UNICODE) . "\n", FILE_APPEND | LOCK_EX);
}
go('/thanks/');
