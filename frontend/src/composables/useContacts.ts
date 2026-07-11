/** 联系人管理 composable
 *
 * 封装联系人 API 调用和状态管理：
 * - 列表加载、搜索、新增、编辑、删除
 * - 写信自动补全用搜索
 * - 往来邮件统计
 * - 一个联系人可关联多个邮箱
 */
import { ref } from 'vue'
import api from '../utils/api'

/** 联系人邮箱项 */
export interface ContactEmail {
  id: number
  email: string
  is_primary: boolean
}

/** 联系人数据结构 */
export interface ContactItem {
  id: number
  name: string
  emails: ContactEmail[]
  phone: string
  company: string
  remark: string
  group_name: string
}

/** 写信自动补全用搜索结果项（扁平化：一个邮箱一条记录） */
export interface ContactSuggestion {
  contact_id: number
  name: string
  email: string
}

/** 往来邮件统计 */
export interface ContactStats {
  count: number
  last_date: string
}

/** 格式化联系人显示文本（姓名 <邮箱> 格式） */
export function formatContactTag(item: { name: string; email: string }): string {
  return item.name ? `${item.name} <${item.email}>` : item.email
}

export function useContacts() {
  const contacts = ref<ContactItem[]>([])
  const loading = ref(false)

  /** 加载联系人列表（可传搜索关键词） */
  async function loadContacts(search = '') {
    loading.value = true
    try {
      const data = await api.get('/contacts', { params: search ? { search } : {} }) as any
      contacts.value = data.contacts || []
    } finally {
      loading.value = false
    }
  }

  /** 新增联系人，emails 为邮箱数组，第一个为主邮箱 */
  async function addContact(data: { name: string; emails: string[]; phone?: string; company?: string; remark?: string; group_name?: string }): Promise<boolean> {
    await api.post('/contacts', data)
    return true
  }

  /** 更新联系人 */
  async function editContact(id: number, data: { name: string; emails: string[]; phone?: string; company?: string; remark?: string; group_name?: string }): Promise<boolean> {
    await api.put(`/contacts/${id}`, { ...data, id })
    return true
  }

  /** 删除联系人 */
  async function removeContact(id: number): Promise<boolean> {
    await api.delete(`/contacts/${id}`)
    return true
  }

  /** 搜索联系人（写信自动补全用），展开 emails 数组返回扁平化结果，最多 10 条 */
  async function searchContacts(q: string): Promise<ContactSuggestion[]> {
    if (!q || q.length < 1) return []
    const data = await api.get('/contacts/search', { params: { q } }) as any
    const results: ContactSuggestion[] = []
    for (const contact of (data.results || [])) {
      for (const emailObj of (contact.emails || [])) {
        results.push({
          contact_id: contact.id,
          name: contact.name,
          email: emailObj.email,
        })
      }
    }
    // 按邮箱地址排序，返回前 10 条
    return results.slice(0, 10)
  }

  /** 快速添加联系人（邮件详情页用），邮箱已存在则返回已有记录 */
  async function quickAddContact(name: string, email: string): Promise<ContactItem> {
    return await api.post('/contacts/quick-add', { name, email }) as any
  }

  /** 获取与某邮箱的往来邮件统计 */
  async function getContactStats(contactId: number, email: string): Promise<ContactStats> {
    return await api.get(`/contacts/${contactId}/stats`, { params: { email } }) as any
  }

  return {
    contacts,
    loading,
    loadContacts,
    addContact,
    editContact,
    removeContact,
    searchContacts,
    quickAddContact,
    getContactStats,
  }
}
