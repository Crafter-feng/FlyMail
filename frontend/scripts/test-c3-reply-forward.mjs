function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
function plainTextToSafeHtml(text) {
  if (!text) return '';
  return escapeHtml(text).replace(/\r\n|\r|\n/g, '<br>');
}
// simulate renderMailBody: prefer html sanitize-lite, else plain text
function renderMailBody(bodyHtml, bodyText) {
  if (bodyHtml) {
    return String(bodyHtml)
      .replace(/<script[\s\S]*?<\/script>/gi, '')
      .replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, '');
  }
  return plainTextToSafeHtml(bodyText);
}
function buildReplyDraft(msg) {
  const safeBody = renderMailBody(msg.body_html, msg.body_text);
  return { body_html: '<br><br><blockquote>' + safeBody + '</blockquote>' };
}
function buildForwardDraft(msg) {
  const safeFrom = escapeHtml(msg.from_addr || '');
  const safeSubject = escapeHtml(msg.subject || '');
  const safeDate = escapeHtml(msg.date || '');
  const safeBody = renderMailBody(msg.body_html, msg.body_text);
  return {
    body_html:
      '<p>发件人: ' + safeFrom + '</p><p>主题: ' + safeSubject + '</p><p>日期: ' + safeDate +
      '</p><div>' + safeBody + '</div>',
  };
}
let fail = 0;
function assert(cond, msg) {
  if (!cond) { console.error('FAIL', msg); fail++; }
  else console.log('PASS', msg);
}
const reply = buildReplyDraft({ body_html: '', body_text: 'Hi <img src=x onerror=alert(1)>' });
assert(!reply.body_html.includes('<img'), 'reply plain XSS escaped (no tag)');
assert(reply.body_html.includes('&lt;img'), 'reply plain XSS escaped entities');

const replyHtml = buildReplyDraft({ body_html: '<p>ok</p><script>alert(1)</script><img src=x onerror=alert(2)>', body_text: '' });
assert(!replyHtml.body_html.includes('<script'), 'reply html strips script');
assert(!/onerror\s*=/i.test(replyHtml.body_html), 'reply html strips onerror');
assert(replyHtml.body_html.includes('<p>ok</p>'), 'reply keeps safe p');

const fwd = buildForwardDraft({
  from_addr: 'Evil <img src=x onerror=alert(3)>',
  subject: '<script>x</script>',
  date: '2026-01-01 <b>x</b>',
  body_html: '',
  body_text: 'Body <svg onload=alert(4)>',
});
assert(fwd.body_html.includes('&lt;img'), 'fwd from escaped');
assert(fwd.body_html.includes('&lt;script&gt;'), 'fwd subject escaped');
assert(fwd.body_html.includes('&lt;b&gt;'), 'fwd date escaped');
assert(fwd.body_html.includes('&lt;svg'), 'fwd body escaped');
assert(!fwd.body_html.includes('<img src=x'), 'fwd no raw img from header');
console.log(fail === 0 ? 'ALL_PASS' : 'HAS_FAIL=' + fail);
process.exit(fail === 0 ? 0 : 1);
