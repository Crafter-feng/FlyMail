/** 联系人名称映射 composable
 *
 * 用于邮件列表显示发件人名称：
 * - 加载所有联系人，构建 邮箱→姓名 的映射表
 * - 提供 displayName(from_addr) 方法，优先返回联系人姓名
 * - 多个组件共享同一份缓存（模块级单例），避免重复请求
 */
import { ref } from 'vue'
import api from '../utils/api'
import { extractEmails, extractName } from '../utils/mail-helpers'

/** 模块级单例：邮箱→姓名 映射表，所有组件共享 */
const emailNameMap = ref<Map<string, string>>(new Map())
const loaded = ref(false)
const loading = ref(false)

/** 加载所有联系人，构建邮箱→姓名映射（已加载则跳过） */
async function loadMap(): Promise<void> {
  if (loaded.value || loading.value) return
  loading.value = true
  try {
  const data = await api.get('/contacts') as any
  const map = new Map<string, string>()
  for (const contact of (data.contacts || [])) {
  const name = contact.name?.trim()
  if (!name) continue
  for (const emailObj of (contact.emails || [])) {
  const email = emailObj.email?.toLowerCase().trim()
  if (email) map.set(email, name)
  }
  }
  emailNameMap.value = map
  loaded.value = true
  } finally {
  loading.value = false
  }
}

/** 强制重新加载映射表（新增联系人后调用） */
async function reloadMap(): Promise<void> {
  loaded.value = false
  await loadMap()
}

/**
 * 根据邮件 from_addr 获取显示名
 * 优先级：联系人姓名 > 原始地址中的姓名 > 邮箱前缀
 * 输入: "张三 <zhangsan@qq.com>" 或 "zhangsan@qq.com"
 */
function displayName(fromAddr: string): string {
  if (!fromAddr) return '未知'
  // 先从地址中提取邮箱，查映射表
  const emails = extractEmails(fromAddr)
  for (const email of emails) {
  const name = emailNameMap.value.get(email.toLowerCase())
  if (name) return name
  }
  // 未命中联系人，走原始 extractName 逻辑
  return extractName(fromAddr)
}

export function useContactNameMap() {
  return {
  displayName,
  loadMap,
  reloadMap,
  loading,
  }
}
