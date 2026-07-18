from pydantic import BaseModel
import time


class Account(BaseModel):
  model_config = {"validate_assignment": True}  # 允许修改字段值（如 _ensure_gmail_token 更新 credentials_json）

  id: str
  user_uid: str
  email: str
  provider: str
  credentials_json: str = ""
  status: str = "disconnected"
  remark: str = ""
  group_name: str = ""
  hide_email: bool = False  # 是否隐藏邮箱地址，只显示备注名
  sort_order: int = 0  # 手动排序序号（拖拽排序）
  created_at: float = 0.0
  updated_at: float = 0.0


class CachedMessage(BaseModel):
  id: str
  account_id: str
  user_uid: str
  uid: int
  folder: str
  subject: str
  from_addr: str
  to_addr: str
  cc: str = ""  # 抄送人（缓存到数据库，回复时可用）
  date: str
  is_read: bool = False
  is_starred: bool = False
  has_attachments: bool = False  # 是否有附件
  body_text: str = ""
  body_html: str = ""
  # RFC Message-ID，供回复线程头使用；列表摘要 UPSERT 用 COALESCE 保留
  message_id: str = ""
  cached_at: float = 0.0


class Notification(BaseModel):
  """通知记录（新邮件、定时发送结果等）

  新邮件类通知尽量自带定位字段与摘要，支撑点击跳转详情与后期外发通道。
  """
  id: str  # 唯一ID
  user_uid: str  # 飞牛OS 用户ID
  account_id: str  # 关联的邮箱账户ID
  provider: str  # 邮箱平台：qq / gmail / netease
  email: str  # 邮箱地址
  folder: str  # 文件夹
  is_read: bool = False  # 是否已读
  created_at: float = 0.0  # 通知创建时间戳
  type: str = "new_mail"  # 通知类型：new_mail / schedule_success / schedule_failed / backup_success / backup_failed
  message: str = ""  # 通知描述文本（新邮件优先为主题）
  # 定位（点击跳详情）
  message_cache_id: str = ""
  message_uid: int = 0
  rfc_message_id: str = ""
  # 摘要（列表/外发）
  subject: str = ""
  from_addr: str = ""
  to_addr: str = ""
  cc: str = ""
  mail_date: str = ""
  body_preview: str = ""
  has_attachments: bool = False
  batch_count: int = 1
  extra_json: str = ""



class Signature(BaseModel):
  """签名模板（支持多模板管理）"""
  id: int = 0  # 自增主键
  name: str = ""  # 模板名称，如"工作签名"
  content_html: str = ""  # 富文本 HTML 内容
  is_default: int = 0  # 是否默认签名 (0/1)
  account_id: str = ""  # 关联账号ID（空=全局）
  user_uid: str = ""  # 用户隔离字段，飞牛OS 多用户场景下区分归属
  created_at: float = 0.0  # 创建时间
  updated_at: float = 0.0  # 更新时间


class ContactEmail(BaseModel):
  """联系人邮箱（一个联系人可关联多个邮箱）"""
  id: int = 0  # 自增主键
  contact_id: int = 0  # 关联的联系人ID
  email: str = ""  # 邮箱地址
  is_primary: bool = False  # 是否主邮箱


class Contact(BaseModel):
  """联系人（按 user_uid 隔离，支持多个邮箱）"""
  id: int = 0  # 自增主键
  user_uid: str = ""  # 用户隔离字段
  name: str = ""  # 显示名
  emails: list[ContactEmail] = []  # 邮箱列表（一个联系人可多个邮箱）
  phone: str = ""  # 联系电话
  company: str = ""  # 工作单位
  remark: str = ""  # 备注
  group_name: str = ""  # 分组名
  created_at: float = 0.0  # 创建时间
  updated_at: float = 0.0  # 更新时间
