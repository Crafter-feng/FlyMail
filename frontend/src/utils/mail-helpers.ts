/** 邮件相关公共工具函数 */

// 期望输入格式："张三 <zhangsan@qq.com>" 或纯 "zhangsan@qq.com"
/** 从邮箱地址提取显示名 */
export function extractName(addr: string): string {
  if (!addr) return '未知'
  const match = addr.match(/^(.+?)\s*<.*>$/)
  if (match) return match[1].replace(/"/g, '').trim()
  return addr.split('@')[0]
}

/**
 * 从地址字符串中提取纯邮箱地址数组
 * 输入: "张三 <a@qq.com>, 李四 <b@qq.com>" 或 "a@qq.com, b@qq.com"
 * 输出: ["a@qq.com", "b@qq.com"]
 */
export function extractEmails(addrStr: string): string[] {
  if (!addrStr) return []
  const emails = addrStr.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g)
  return emails || []
}

/** 地址项：名字 + 邮箱 */
export interface AddressItem {
  name: string  // 显示名（无名字时用邮箱前缀）
  email: string  // 纯邮箱地址（小写）
}

/**
 * 解析地址字符串为 {name, email} 数组
 * 支持格式：
 *  "张三" <a@qq.com>, "李四" <b@qq.com>
 *  张三 <a@qq.com>, b@qq.com
 *  a@qq.com, b@qq.com
 *
 * 用于邮件详情页展示收件人/抄送人列表
 */
export function parseAddressList(addrStr: string): AddressItem[] {
  if (!addrStr || !addrStr.trim()) return []
  const result: AddressItem[] = []
  // 正则匹配两种格式：1. "Name" <email>  2. 纯 email
  const regex = /(?:"?([^"<]*?)"?\s*<([^>]+)>)|([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/g
  let match: RegExpExecArray | null
  while ((match = regex.exec(addrStr)) !== null) {
  if (match[2]) {
  // "Name" <email> 格式：优先用名字，无名字时用邮箱前缀
  const name = match[1].trim().replace(/"/g, '')
  const email = match[2].trim().toLowerCase()
  result.push({ name: name || email.split('@')[0], email })
  } else if (match[3]) {
  // 纯 email 格式：名字用邮箱前缀
  const email = match[3].toLowerCase()
  result.push({ name: email.split('@')[0], email })
  }
  }
  return result
}

/** 获取头像首字母 */
export function getInitial(addr: string): string {
  const name = extractName(addr)
  return name.charAt(0).toUpperCase()
}

/** 根据邮箱地址生成头像颜色 */
const AVATAR_COLORS = ['#007AFF', '#34C759', '#FF9500', '#FF3B30', '#AF52DE', '#5AC8FA', '#FF2D55', '#64D2FF']
export function getAvatarColor(addr: string): string {
  let hash = 0
  for (let i = 0; i < (addr || '').length; i++) {
  hash = addr.charCodeAt(i) + ((hash << 5) - hash)
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length]
}

/** 格式化邮件时间（列表用，简洁格式） */
export function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  try {
  const d = new Date(dateStr)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  if (isToday) return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  const isThisYear = d.getFullYear() === now.getFullYear()
  if (isThisYear) return `${d.getMonth() + 1}月${d.getDate()}日`
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()}`
  } catch {
  return dateStr
  }
}

/** 格式化邮件时间（详情页用，完整格式） */
export function formatDetailDate(dateStr: string): string {
  if (!dateStr) return ''
  try {
  const d = new Date(dateStr)
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const weekday = weekdays[d.getDay()]
  const hour = String(d.getHours()).padStart(2, '0')
  const minute = String(d.getMinutes()).padStart(2, '0')
  return `${year}年${month}月${day}日 (${weekday}) ${hour}:${minute}`
  } catch {
  return dateStr
  }
}

/**
 * 将地址列表格式化为可读字符串
 * - 有姓名："姓名 <邮箱>"
 * - 无姓名：直接显示邮箱
 * - 多个地址用"；"分隔
 *
 * 用于详情页收件人/抄送人行的纯文本展示
 */
export function formatAddressList(addrStr: string): string {
  const list = parseAddressList(addrStr)
  if (list.length === 0) return ''
  return list.map((a) => {
  // 如果 name 就是邮箱前缀且与 email 前缀一致，直接显示完整邮箱
  // 否则显示"姓名 <邮箱>"
  if (a.name === a.email.split('@')[0]) {
  return a.email
  }
  return `${a.name} <${a.email}>`
  }).join('；')
}

/** 格式化文件大小 */
export function formatFileSize(bytes: number): string {
  if (!bytes || bytes <= 0) return ''
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

/** 下载附件 */
export function downloadAttachment(params: {
  messageId: string
  accountId: string
  folder: string
  partNumber: number
  filename: string
}): void {
  const { messageId, accountId, folder, partNumber, filename } = params
  // 使用 /app/flymail/api 前缀，确保走 Vite 开发代理（vite.config.ts 匹配 /app/flymail/api）
  // 生产环境通过 StripPrefixMiddleware 自动剥离 /app/flymail 前缀
  const url = `/app/flymail/api/messages/${messageId}/attachments/${partNumber}?account_id=${accountId}&folder=${encodeURIComponent(folder)}`
  // 通过创建临时 a 元素触发浏览器原生下载
  const link = document.createElement('a')
  link.href = url
  link.download = filename || 'attachment'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

/** 获取文件夹显示数量（收件箱显示未读数，其他显示总数） */
export function getFolderCount(folder: { name?: string; path?: string; unread_count?: number; total_count?: number }): number {
  if (!folder) return 0
  // 兼容两种判断方式：按中文名或按 IMAP 路径
  const isInbox = folder.name === '收件箱' || folder.path?.toUpperCase() === 'INBOX'
  return isInbox ? (folder.unread_count || 0) : (folder.total_count || 0)
}
