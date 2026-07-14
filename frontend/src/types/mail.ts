/** 邮件相关类型定义 */

/** 附件 */
export interface Attachment {
  filename: string
  content_type: string
  size: number
  part_number: number
  content_id: string // 内联图片的 CID 引用，如 <img src="cid:xxx">
  is_inline: boolean // true=内嵌附件（如邮件正文图片），false=普通附件
}

/** 邮件消息 */
export interface Message {
  id: string
  uid?: number // IMAP UID，用于跨标签页同步等场景
  from_addr: string // 格式："发件人名 <email@domain.com>" 或纯邮箱地址
  to_addr?: string // 收件人（逗号分隔的地址字符串）
  cc?: string // 抄送人（逗号分隔的地址字符串，回复时用于填充抄送列表）
  reply_to?: string // 回复地址（Reply-To 头，为空时用 from_addr）
  subject: string
  date: string
  is_read: boolean
  body_text?: string
  body_html?: string
  attachments?: Attachment[]
  has_attachments?: boolean
  account_id?: string // 聚合视图专用：邮件所属账号 ID
  account_email?: string // 聚合视图专用：邮件所属账号邮箱
  account_provider?: string // 聚合视图专用：邮件所属邮箱提供商
  folder?: string // IMAP 文件夹路径，如 INBOX、Sent Messages
}

// ==================== 邮件备份相关类型 ====================

/** 备份设置中的账号项 */
export interface BackupAccount {
  id: string
  email: string
  provider: string
  selected: boolean // 是否已加入备份列表
}

/** 可用的备份目录项 */
export interface BackupDir {
  path: string // 空字符串表示使用默认数据目录
  label: string
  writable: boolean
  exists: boolean
}

/** GET /api/backup/settings 返回结构 */
export interface BackupSettings {
  enabled: boolean
  account_ids: string[]
  target_dir: string
  available_dirs: BackupDir[]
  current_root: string
  accounts: BackupAccount[]
}

/** 备份状态中的单账号统计 */
export interface BackupAccountStatus {
  account_id: string
  count: number
  deleted_count: number
  last_archived: number
  email: string
  provider: string
}

/** 归档文件夹列表项 */
export interface BackupFolder {
  folder: string
  count: number
  deleted_count: number
}

/** GET /api/backup/status 返回结构 */
export interface BackupStatus {
  total: number
  deleted: number
  last_archived: number
  accounts: BackupAccountStatus[]
}

/** 归档邮件列表项（对应 message_archive 表行） */
export interface ArchivedMessage {
  id: number
  user_uid?: string
  account_id: string
  folder: string
  uid: number
  message_id?: string
  subject: string
  from_addr: string
  to_addr?: string
  cc?: string
  date: string
  size?: number
  eml_path?: string
  flags?: string
  has_attachments: number
  archived_at: number
  is_deleted_on_server: number
  deleted_at?: number
}

/** 归档邮件详情中的附件（.eml 解析得到，含 part_number 用于下载） */
export interface BackupAttachment {
  filename: string
  content_type: string
  size: number
  part_number: number
  is_inline: boolean
}

/** GET /api/backup/messages/{account_id}/{folder}/{uid} 返回结构 */
export interface ArchivedMessageDetail {
  id: string
  uid: number
  subject: string
  from_addr: string
  to_addr?: string
  cc?: string
  reply_to?: string
  date: string
  body_text?: string
  body_html?: string
  attachments: BackupAttachment[]
  has_attachments: boolean
  is_deleted_on_server: number
  archived_at: number
  size: number
}
