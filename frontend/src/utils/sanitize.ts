/** HTML 净化配置，防止 XSS 攻击 */
import DOMPurify from 'dompurify'

// 允许的标签白名单
const ALLOWED_TAGS = [
  'a', 'b', 'br', 'div', 'em',
  // font/bgcolor/face/size 等已废弃标签：为兼容老式邮件客户端的 HTML 邮件而保留
  'font', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'hr', 'i', 'img', 'li', 'ol', 'p', 'pre', 'span', 'strong', 'sub', 'sup',
  'table', 'tbody', 'td', 'th', 'thead', 'tr', 'u', 'ul', 'blockquote', 'cite',
]

// 允许的属性白名单
const ALLOWED_ATTR = [
  'href', 'src', 'alt', 'style', 'class', 'id',
  // target 属性配合下面的 afterSanitizeAttributes hook 强制设置 _blank
  'target', 'rel',
  'width', 'height', 'color', 'size', 'face',
  'align', 'valign', 'bgcolor', 'colspan', 'rowspan',
]

/**
 * 注册 DOMPurify 钩子：净化属性后，强制给所有 <a> 标签添加安全属性
 *
 * 解决飞牛 OS 桌面端（嵌入式 WebView）中邮件链接无法跳转的问题：
 * 1. 邮件 HTML 中的 <a> 大多没有 target="_blank"，默认 _self 会在当前 WebView 内导航，
 *    被飞牛桌面壳的安全策略拦截，导致点击无反应
 * 2. 强制 target="_blank" 让链接在新窗口打开，配合 rel="noopener noreferrer" 防止
 *    新窗口通过 window.opener 引用原窗口（安全加固）
 *
 * 钩子是全局的，但本模块只加载一次，不会重复注册。
 */
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    // 强制在新窗口打开，避免在当前 WebView 内导航被拦截
    node.setAttribute('target', '_blank')
    // 安全加固：防止新窗口通过 window.opener 操作原窗口
    node.setAttribute('rel', 'noopener noreferrer')
  }
})

/** 净化邮件 HTML，防止 XSS 注入（移除 script、事件处理器等危险标签） */
export function sanitizeHtml(html: string | undefined | null): string {
  if (!html) return ''
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ALLOW_DATA_ATTR: false,
  })
}

/**
 * 邮件正文链接点击事件委托处理
 *
 * 配合 sanitizeHtml 的 DOMPurify hook 使用，作为飞牛 OS 桌面端的二级保障：
 * - hook 已强制 target="_blank"，但 WebView 环境可能仍拦截 window.open
 * - 这里通过事件委托主动调用 window.open，确保链接能在外部浏览器打开
 * - 同时过滤 javascript: 等危险协议，只允许 http/https/mailto
 *
 * 用法：在渲染邮件正文的容器上绑定 @click="handleMailLinkClick"
 */
export function handleMailLinkClick(e: MouseEvent) {
  // 通过 closest 向上查找被点击元素所在的 <a> 标签（兼容 <a><img></a> 等嵌套结构）
  const target = e.target as HTMLElement | null
  const link = target?.closest('a')
  if (!link) return

  const href = link.getAttribute('href') || ''
  // 只允许 http/https/mailto 协议，拦截 javascript:、data: 等危险协议
  if (!/^(https?:|mailto:)/i.test(href)) {
    e.preventDefault()
    return
  }

  // 阻止默认导航（避免在当前 WebView 内跳转被飞牛桌面壳拦截导致白屏）
  e.preventDefault()
  // 主动调用 window.open，飞牛 OS 桌面壳会接管并用系统浏览器打开
  window.open(href, '_blank', 'noopener,noreferrer')
}
