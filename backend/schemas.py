from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
  status: str = Field(description="服务状态")
  app: str = Field(description="应用名称")
  version: str = Field(description="版本号")


class UserResponse(BaseModel):
  uid: str = Field(description="飞牛OS 用户ID")
  username: str = Field(description="飞牛OS 用户名")


class SettingsResponse(BaseModel):
  gmail_proxy_enabled: bool = Field(default=False, description="是否启用 HTTP 代理（网络受限环境访问 Google）")
  gmail_proxy_url: str = Field(default="", description="HTTP 代理地址，如 http://127.0.0.1:7890")


class SettingsUpdateResponse(BaseModel):
  success: bool = Field(description="是否保存成功")
  message: str = Field(description="结果消息")


class SettingsUpdateRequest(BaseModel):
  """更新应用设置请求模型，所有字段可选。"""
  gmail_proxy_enabled: Optional[bool] = Field(default=None, description="是否启用 HTTP 代理")
  gmail_proxy_url: Optional[str] = Field(default=None, max_length=500, description="HTTP 代理地址")


class ProxyTestRequest(BaseModel):
  """测试 Gmail HTTP 代理连通性请求。"""
  proxy_url: str = Field(..., max_length=500, description="HTTP 代理地址，如 http://127.0.0.1:7890")


class ProxyTestResponse(BaseModel):
  """测试 Gmail HTTP 代理连通性响应。"""
  success: bool = Field(description="代理是否可用")
  message: str = Field(description="结果说明（中文）")
  latency_ms: int = Field(default=0, description="探测耗时毫秒")
  target: str = Field(default="", description="实际探测的目标主机:端口")


class AuthUrlResponse(BaseModel):
  auth_url: str = Field(description="第三方授权页面URL，前端跳转到此地址")
  provider: str = Field(description="邮箱平台类型")


class AuthUrlRequest(BaseModel):
  provider: str = Field(default="gmail", description="邮箱平台类型：gmail / outlook")


class AuthCodeAccountRequest(BaseModel):
  email: str = Field(description="邮箱地址")
  auth_code: str = Field(description="邮箱授权码或应用专用密码")
  is_exmail: bool = Field(default=False, description="是否为腾讯企业邮箱")


class CustomAccountRequest(BaseModel):
  """自定义邮箱添加请求（标准 IMAP/SMTP，用户填写服务器配置）"""
  email: str = Field(..., description="邮箱地址")
  auth_code: str = Field(..., description="授权码或登录密码")
  imap_host: str = Field(..., description="IMAP 服务器地址")
  imap_port: int = Field(default=993, description="IMAP 端口（SSL 默认 993，不加密/STARTTLS 默认 143）")
  imap_ssl: str = Field(default="ssl", description="IMAP 加密方式: ssl（直连）| starttls | none（不加密）")
  smtp_host: str = Field(..., description="SMTP 服务器地址")
  smtp_port: int = Field(default=465, description="SMTP 端口（SSL 默认 465，STARTTLS 默认 587）")
  smtp_ssl: str = Field(default="ssl", description="SMTP 加密方式: ssl（直连）| starttls")


class AccountInfo(BaseModel):
  id: str = Field(description="账号唯一ID")
  email: str = Field(description="邮箱地址")
  provider: str = Field(description="邮箱平台")
  status: str = Field(description="连接状态")
  remark: str = Field(description="备注名")
  group_name: str = Field(description="分组名称")
  hide_email: bool = Field(description="是否隐藏邮箱地址")
  sort_order: int = Field(default=0, description="排序序号")
  created_at: float = Field(description="创建时间戳")


class AccountListResponse(BaseModel):
  accounts: List[AccountInfo] = Field(description="账号列表")


class AccountAddResponse(BaseModel):
  success: bool = Field(description="是否添加成功")
  account: AccountInfo = Field(description="新创建的账号信息")


class AccountTestResponse(BaseModel):
  success: bool = Field(description="连接是否成功")
  status: str = Field(description="连接状态")
  error: str = Field(default="", description="错误信息（连接失败时）")


class AccountUpdateRequest(BaseModel):
  remark: str = Field(default="", description="备注名")
  group_name: str = Field(default="", description="分组名称")
  hide_email: bool = Field(default=False, description="是否隐藏邮箱地址")


class StatusResponse(BaseModel):
  success: bool = Field(default=True, description="是否成功")


class DeleteResponse(BaseModel):
  success: bool = Field(description="是否删除成功")


class MessageResponse(BaseModel):
  success: bool = Field(description="是否成功")
  message: str = Field(default="", description="结果消息")


class FolderItem(BaseModel):
  name: str = Field(description="文件夹显示名")
  path: str = Field(description="IMAP 文件夹路径")
  unread_count: int = Field(default=0, description="未读邮件数")
  total_count: int = Field(default=0, description="邮件总数")


class FolderCountItem(BaseModel):
  total: int = Field(description="邮件总数")
  unread: int = Field(description="未读邮件数")


class FolderResponse(BaseModel):
  folders: List[FolderItem] = Field(description="文件夹列表")
  account_id: str = Field(default="", description="账号ID")
  error: str = Field(default="", description="错误信息")
  reconnecting: bool = Field(default=False, description="邮箱连接异常时是否正在重连")


class FolderCountsResponse(BaseModel):
  counts: Dict[str, FolderCountItem] = Field(description="文件夹计数，key 为文件夹路径")
  account_id: str = Field(default="", description="账号ID")
  error: str = Field(default="", description="错误信息")
  reconnecting: bool = Field(default=False, description="邮箱连接异常时是否正在重连")


class AttachmentItem(BaseModel):
  filename: str = Field(default="", description="附件文件名")
  content_type: str = Field(default="", description="MIME 类型")
  size: int = Field(default=0, description="文件大小（字节）")
  part_number: int = Field(default=0, description="IMAP part 编号，用于下载附件")
  content_id: str = Field(default="", description="Content-ID，内嵌图片标识")
  is_inline: bool = Field(default=False, description="是否为内嵌附件")


class MessageItem(BaseModel):
  id: str = Field(description="邮件ID")
  uid: int = Field(description="IMAP UID")
  subject: str = Field(default="", description="邮件主题")
  from_addr: str = Field(default="", description="发件人")
  to_addr: str = Field(default="", description="收件人")
  cc: str = Field(default="", description="抄送人（逗号分隔的地址字符串）")
  date: str = Field(default="", description="邮件日期")
  is_read: bool = Field(default=False, description="是否已读")
  is_starred: bool = Field(default=False, description="是否星标")
  folder: str = Field(default="INBOX", description="文件夹路径")
  body_text: str = Field(default="", description="纯文本正文")
  body_html: str = Field(default="", description="HTML 正文")
  attachments: List[AttachmentItem] = Field(default=[], description="附件列表")
  has_attachments: bool = Field(default=False, description="是否包含附件")
  # RFC Message-ID（非 IMAP UID），回复时作为 In-Reply-To
  message_id: str = Field(default="", description="RFC Message-ID，用于回复线程")
  account_id: str = Field(default="", description="账号ID，聚合收件箱返回")
  account_email: str = Field(default="", description="账号邮箱，聚合收件箱返回")
  account_provider: str = Field(default="", description="邮箱平台，聚合收件箱返回")


class MessageListResponse(BaseModel):
  messages: List[MessageItem] = Field(description="邮件列表")
  total: int = Field(description="邮件总数")
  unread_total: int = Field(default=0, description="未读邮件总数")
  page: int = Field(description="当前页码")
  page_size: int = Field(description="每页数量")
  account_id: str = Field(default="", description="账号ID")
  error: str = Field(default="", description="错误信息")
  reconnecting: bool = Field(default=False, description="邮箱连接异常时是否正在重连")
  no_accounts: bool = Field(default=False, description="聚合收件箱是否未选择任何账号")
  filter_counts: dict = Field(default={}, description="各筛选条件的计数: {all, unread, read, attachments}")


class PrefetchMessagesRequest(BaseModel):
  message_ids: List[str] = Field(default=[], max_length=50, description="需要预取正文的邮件ID列表，最多50封")
  account_id: str = Field(default="", description="账号ID")
  folder: str = Field(default="INBOX", description="文件夹路径")


class PrefetchMessagesResponse(BaseModel):
  success: bool = Field(default=True, description="是否成功")
  queued: int = Field(default=0, description="已加入后台预取队列的邮件数量")
  prefetched: int = Field(default=0, description="已预取数量；无任务时返回0")


class MarkReadRequest(BaseModel):
  message_id: str = Field(description="邮件ID")
  folder: str = Field(default="INBOX", description="文件夹路径")
  account_id: str = Field(default="", description="账号ID")


class BatchMarkReadRequest(BaseModel):
  message_ids: List[str] = Field(description="邮件ID列表")
  folder: str = Field(default="INBOX", description="文件夹路径")
  account_id: str = Field(default="", description="账号ID")


class BatchMarkReadResponse(BaseModel):
  success: bool = Field(description="是否成功")
  marked: int = Field(description="成功标记数量")


class MarkAllReadRequest(BaseModel):
  """一键全部已读请求：后端自行通过 IMAP SEARCH UNSEEN 获取未读 UID，前端无需传 UID 列表"""
  account_ids: List[str] = Field(description="账号ID列表（聚合视图传多个，邮件视图传单个）")
  folder: str = Field(default="INBOX", description="文件夹路径")


class MarkAllReadAccountResult(BaseModel):
  """单个账号的全部已读结果"""
  account_id: str = Field(description="账号ID")
  email: str = Field(description="邮箱地址")
  marked: int = Field(description="IMAP 标记成功的数量")


class MarkAllReadResponse(BaseModel):
  """一键全部已读响应"""
  success: bool = Field(description="是否成功")
  results: List[MarkAllReadAccountResult] = Field(description="各账号标记结果")
  total_marked: int = Field(description="总计标记数量")


class BatchDeleteRequest(BaseModel):
  message_ids: List[str] = Field(description="邮件ID列表")
  account_id: str = Field(default="", description="账号ID")
  folder: str = Field(default="INBOX", description="文件夹路径")


class BatchDeleteResponse(BaseModel):
  success: bool = Field(description="是否成功")
  deleted: int = Field(description="成功删除数量")


class SendMessageRequest(BaseModel):
  to: str = Field(description="收件人邮箱地址")
  subject: str = Field(description="邮件主题")
  content: str = Field(description="邮件正文")
  html: bool = Field(default=False, description="是否为HTML格式")


class SendMessageResponse(BaseModel):
  success: bool = Field(default=True, description="是否成功")
  message: str = Field(description="结果消息")


class ComposeMessageRequest(BaseModel):
  """写邮件请求模型，支持发送/草稿/定时发送"""

  account_id: str = Field(default="", description="发件账号ID，空则使用第一个账号")
  to: list[str] = Field(default=[], max_length=50, description="收件人列表，最多50人")
  cc: list[str] = Field(default=[], max_length=50, description="抄送列表，最多50人")
  bcc: list[str] = Field(default=[], max_length=50, description="密送列表，最多50人")
  subject: str = Field(default="", max_length=500, description="邮件主题，最多500字符")
  body_html: str = Field(default="", description="HTML格式正文")
  attachments: list[str] = Field(default=[], max_length=20, description="附件文件路径列表，最多20个")
  action: str = Field(default="send", description="操作类型: send=发送, draft=保存草稿, schedule=定时发送")
  schedule_time: str | None = Field(default=None, description="ISO8601定时发送时间（action=schedule时必填）")
  in_reply_to: str | None = Field(default=None, description="回复的邮件Message-ID")
  forward_from: str | None = Field(default=None, description="转发的邮件Message-ID")


class ComposeMessageResponse(BaseModel):
  success: bool = Field(default=True, description="是否成功")
  message: str = Field(description="结果消息")
  job_id: str = Field(default="", description="定时发送任务ID，仅 action=schedule 时返回")


class UploadAttachmentResponse(BaseModel):
  filename: str = Field(description="原始文件名")
  size: int = Field(description="文件大小（字节）")
  path: str = Field(description="服务端临时附件路径，发送邮件时传入 attachments")
  source: str = Field(default="local", description="来源：local=临时上传，nas=授权目录引用")


class RegisterNasAttachmentRequest(BaseModel):
  """从 NAS 授权目录引用附件（不复制，仅登记路径）"""
  path: str = Field(description="授权目录内的文件绝对路径")


class SaveAttachmentToNasRequest(BaseModel):
  """将邮件附件保存到 NAS 授权目录"""
  account_id: str = Field(default="", description="账号 ID")
  folder: str = Field(default="INBOX", description="邮件所在文件夹")
  target_dir: str = Field(description="目标目录（必须在飞牛授权目录内）")
  filename: str = Field(default="", description="可选保存文件名，默认用附件原名")


class SaveAttachmentToNasResponse(BaseModel):
  success: bool = Field(default=True, description="是否成功")
  path: str = Field(description="保存后的完整路径")
  filename: str = Field(description="最终文件名")
  size: int = Field(description="文件大小（字节）")


class SignatureSettingsRequest(BaseModel):
  signature_html: str = Field(default="", description="签名 HTML 内容")
  signature_enabled: bool = Field(default=False, description="是否启用签名")


class SignatureSettingsResponse(BaseModel):
  signature_html: str = Field(default="", description="签名 HTML 内容")
  signature_enabled: int = Field(default=0, description="是否启用签名，1=启用，0=关闭")


class SignatureTemplateRequest(BaseModel):
  name: str = Field(default="", description="签名模板名称")
  content_html: str = Field(default="", description="签名 HTML 内容")
  is_default: bool = Field(default=False, description="是否默认签名")
  account_id: str = Field(default="", description="关联账号ID，空表示全局模板")


class SignatureTemplateUpdateRequest(BaseModel):
  name: Optional[str] = Field(default=None, description="签名模板名称，不传则保持不变")
  content_html: Optional[str] = Field(default=None, description="签名 HTML 内容，不传则保持不变")
  is_default: Optional[bool] = Field(default=None, description="是否默认签名，不传则保持不变")
  account_id: Optional[str] = Field(default=None, description="关联账号ID，不传则保持不变")


class SignatureTemplateItem(BaseModel):
  id: int = Field(description="签名模板ID")
  name: str = Field(description="签名模板名称")
  content_html: str = Field(default="", description="签名 HTML 内容")
  is_default: bool = Field(default=False, description="是否默认签名")
  account_id: str = Field(default="", description="关联账号ID，空表示全局模板")


class SignatureListResponse(BaseModel):
  signatures: List[SignatureTemplateItem] = Field(description="签名模板列表")


class UnifiedSettingsRequest(BaseModel):
  account_ids: List[str] = Field(default=[], max_length=100, description="参与聚合收件箱的账号ID列表，最多100个")


class UnifiedSettingsAccount(BaseModel):
  id: str = Field(description="账号ID")
  email: str = Field(description="邮箱地址")
  provider: str = Field(description="邮箱平台")
  selected: bool = Field(description="是否已选入聚合收件箱")


class UnifiedSettingsResponse(BaseModel):
  account_ids: List[str] = Field(description="已选账号ID列表")
  accounts: List[UnifiedSettingsAccount] = Field(description="可选择的账号列表")


class ScheduledMessagesResponse(BaseModel):
  jobs: List[Dict[str, Any]] = Field(description="待执行的定时发送任务列表")


class NotificationItem(BaseModel):
  id: str = Field(description="通知ID")
  account_id: str = Field(description="账户ID")
  provider: str = Field(description="邮箱平台")
  email: str = Field(description="邮箱地址")
  folder: str = Field(description="文件夹")
  is_read: bool = Field(description="是否已读")
  time: float = Field(description="通知时间（毫秒时间戳）")
  type: str = Field(default="new_mail", description="通知类型：new_mail / schedule_success / schedule_failed")
  message: str = Field(default="", description="通知描述文本")
  message_cache_id: str = Field(default="", description="缓存邮件ID，用于跳转详情")
  message_uid: int = Field(default=0, description="IMAP UID")
  rfc_message_id: str = Field(default="", description="RFC Message-ID")
  subject: str = Field(default="", description="邮件主题")
  from_addr: str = Field(default="", description="发件人")
  to_addr: str = Field(default="", description="收件人")
  cc: str = Field(default="", description="抄送")
  mail_date: str = Field(default="", description="邮件 Date 头")
  body_preview: str = Field(default="", description="正文纯文本截取")
  has_attachments: bool = Field(default=False, description="是否有附件")
  batch_count: int = Field(default=1, description="批量计数，P1 恒为 1")


class NotificationListResponse(BaseModel):
  notifications: List[NotificationItem] = Field(description="通知列表")


class NotificationReadResponse(BaseModel):
  success: bool = Field(description="是否成功")


class NotificationReadAllResponse(BaseModel):
  success: bool = Field(description="是否成功")
  updated: int = Field(description="更新的通知数量")


class NotificationClearResponse(BaseModel):
  success: bool = Field(description="是否成功")
  deleted: int = Field(description="删除的通知数量")


class ErrorResponse(BaseModel):
  error: str = Field(description="错误信息")


# ==================== 联系人相关 ====================


class ContactEmailItem(BaseModel):
  """联系人邮箱项"""
  id: int = Field(default=0, description="邮箱记录ID")
  email: str = Field(description="邮箱地址")
  is_primary: bool = Field(default=False, description="是否主邮箱")


class ContactItem(BaseModel):
  id: int = Field(description="联系人ID")
  name: str = Field(default="", description="姓名")
  emails: List[ContactEmailItem] = Field(default=[], description="邮箱列表（一个联系人可多个邮箱）")
  phone: str = Field(default="", description="电话")
  company: str = Field(default="", description="工作单位")
  remark: str = Field(default="", description="备注")
  group_name: str = Field(default="", description="分组")


class ContactListResponse(BaseModel):
  contacts: List[ContactItem] = Field(description="联系人列表")


class ContactSearchResponse(BaseModel):
  results: List[ContactItem] = Field(description="搜索结果（最多10条）")


class ContactCreateRequest(BaseModel):
  name: str = Field(default="", description="姓名")
  emails: List[str] = Field(default=[], description="邮箱地址列表（第一个为主邮箱）")
  phone: str = Field(default="", description="电话")
  company: str = Field(default="", description="工作单位")
  remark: str = Field(default="", description="备注")
  group_name: str = Field(default="", description="分组")


class ContactUpdateRequest(ContactCreateRequest):
  id: int = Field(description="联系人ID")


class QuickAddContactRequest(BaseModel):
  name: str = Field(default="", description="姓名（从邮件发件人解析）")
  email: str = Field(description="邮箱地址")


class ContactStatsResponse(BaseModel):
  """联系人往来邮件统计"""
  count: int = Field(default=0, description="往来邮件总数")
  last_date: str = Field(default="", description="最近一次联系时间")
