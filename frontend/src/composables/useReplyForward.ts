import { extractEmails } from '../utils/mail-helpers'
import { escapeHtml, renderMailBody } from '../utils/sanitize'
import type { Message } from '../types/mail'

/**
 * 构建回复邮件草稿（角色模式）
 *
 * 规则：
 * - to = 原发件人（Reply-To优先） + 原收件人 - 自己
 * - cc = 原抄送人 - 自己 - 已在to中的邮箱
 *
 * 示例：原邮件 A发件、B+C收件、D+E+F抄送
 * - B回复：to=[A,C]，cc=[D,E,F]
 * - D回复：to=[A,B,C]，cc=[E,F]
 *
 * 安全（C3）：
 * - 引用正文必须经 renderMailBody 净化/转义后再拼入 body_html，
 *   防止恶意邮件在「回复/转发」编辑器中通过未净化 HTML 触发 XSS，
 *   以及把危险载荷原样转发给收件人。
 *
 * @param msg 原始邮件
 * @param myEmail 当前账号邮箱（用于排除自己）
 * @param accountId 发件账号ID
 */
export function buildReplyDraft(msg: Message, myEmail: string, accountId: string) {
  // 回复目标：Reply-To 优先，否则用 From（保留原始格式，含显示名）
  const replyToAddr = msg.reply_to || msg.from_addr
  const replyToEmails = extractEmails(replyToAddr)

  // 分别解析原收件人和原抄送人
  const originalToEmails = extractEmails(msg.to_addr || '')
  const originalCcEmails = extractEmails(msg.cc || '')

  // 新 To = 原发件人 + 原收件人（排除自己和已在replyTo中的邮箱，避免重复）
  const toList = [
    replyToAddr,
    ...originalToEmails.filter(
      (e) => e !== myEmail && !replyToEmails.includes(e),
    ),
  ]

  // 新 Cc = 原抄送人（排除自己和已在To中的邮箱）
  const toEmailSet = new Set([
    ...replyToEmails,
    ...originalToEmails.filter((e) => e !== myEmail),
  ])
  const ccList = originalCcEmails.filter(
    (e) => e !== myEmail && !toEmailSet.has(e),
  )

  const subject = msg.subject?.startsWith('Re:') ? msg.subject : `Re: ${msg.subject || ''}`
  const safeBody = renderMailBody(msg.body_html, msg.body_text)
  const quoteHtml = `<br><br><blockquote style="border-left:3px solid #ccc;padding-left:10px;color:#666;">${safeBody}</blockquote>`

  // 线程头必须用 RFC Message-ID，不能用 IMAP UID（msg.id）
  const rfcMessageId = (msg.message_id || '').trim()
  return {
    to: toList,
    cc: ccList,
    subject,
    body_html: quoteHtml,
    // 无 message_id 时传空，避免错误地把 UID 当成 In-Reply-To
    in_reply_to: rfcMessageId,
    account_id: accountId,
  }
}

/**
 * 构建转发邮件草稿
 *
 * 安全（C3）：
 * - 发件人/主题/日期等元数据用 escapeHtml 转义
 * - 正文用 renderMailBody 净化或转义后再嵌入
 *
 * @param msg 原始邮件
 * @param accountId 发件账号ID
 */
export function buildForwardDraft(msg: Message, accountId: string) {
  const subject = msg.subject?.startsWith('Fwd:') ? msg.subject : `Fwd: ${msg.subject || ''}`
  const safeFrom = escapeHtml(msg.from_addr || '')
  const safeSubject = escapeHtml(msg.subject || '')
  const safeDate = escapeHtml(msg.date || '')
  const safeBody = renderMailBody(msg.body_html, msg.body_text)
  const fwdHtml = `<br><br><p>---------- 转发的邮件 ----------</p><p>发件人: ${safeFrom}</p><p>主题: ${safeSubject}</p><p>日期: ${safeDate}</p><hr/><div>${safeBody}</div>`
  return {
    to: [] as string[],
    subject,
    body_html: fwdHtml,
    account_id: accountId,
  }
}
