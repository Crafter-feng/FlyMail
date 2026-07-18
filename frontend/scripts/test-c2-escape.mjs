function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
function plainTextToSafeHtml(text) {
  if (!text) return '';
  return escapeHtml(text).replace(/\r\n|\r|\n/g, '<br>');
}
let fail = 0;
function assert(cond, msg) {
  if (!cond) { console.error('FAIL', msg); fail++; }
  else console.log('PASS', msg);
}
const xss = 'Hello <img src=x onerror=alert(1)> <script>alert(2)</script>';
const out = plainTextToSafeHtml(xss);
assert(!out.includes('<img'), 'no raw img tag');
assert(!out.includes('<script'), 'no raw script tag');
assert(out.includes('&lt;img'), 'escaped img');
assert(out.includes('&lt;script'), 'escaped script');
assert(plainTextToSafeHtml('a\nb\r\nc') === 'a<br>b<br>c', 'newlines to br');
assert(escapeHtml('a&b') === 'a&amp;b', 'amp');
const vulnerable = '' || xss;
assert(vulnerable.includes('<img'), 'old path injects (baseline)');
assert(!plainTextToSafeHtml(xss).includes('<img'), 'new path safe');
console.log(fail === 0 ? 'ALL_PASS' : 'HAS_FAIL=' + fail);
process.exit(fail === 0 ? 0 : 1);