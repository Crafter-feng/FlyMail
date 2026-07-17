<template>
  <div class="contact-page">
  <!-- ============ 左侧：联系人列表 ============ -->
  <aside class="contact-sidebar" :class="{ 'mobile-hidden': selectedId && isMobile }">
  <!-- 顶部操作栏 -->
  <div class="sidebar-header">
  <div class="search-box">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
  </svg>
  <input v-model="searchKeyword" placeholder="搜索姓名或邮箱" class="search-input" />
  </div>
  <button class="btn-add" @click="openAddDialog()">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
  <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
  </svg>
  新增
  </button>
  </div>

  <!-- 加载状态 -->
  <div v-if="loading" class="state-box">
  <div class="spinner"></div>
  <span>加载中...</span>
  </div>

  <!-- 空状态 -->
  <div v-else-if="filteredContacts.length === 0" class="state-box empty">
  <div class="empty-icon">
  <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2">
  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
  <path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
  </div>
  <p class="state-title">{{ searchKeyword ? '未找到匹配的联系人' : '还没有联系人' }}</p>
  <p class="state-desc">{{ searchKeyword ? '试试其他关键词' : '点击「新增」按钮添加联系人' }}</p>
  </div>

  <!-- 联系人列表 -->
  <div v-else class="contact-list">
  <div
  v-for="contact in filteredContacts"
  :key="contact.id"
  class="contact-item"
  :class="{ active: contact.id === selectedId }"
  @click="selectContact(contact.id)"
  >
  <div class="avatar-sm" :style="{ background: getAvatarColor(contact.name || primaryEmail(contact)) }">
  {{ avatarLetter(contact) }}
  </div>
  <div class="item-info">
  <div class="item-name">{{ contact.name || '(未命名)' }}</div>
  <div class="item-email">{{ primaryEmail(contact) }}</div>
  </div>
  <span v-if="contact.emails.length > 1" class="email-count" :title="`共 ${contact.emails.length} 个邮箱`">
  {{ contact.emails.length }}
  </span>
  </div>
  </div>
  </aside>

  <!-- ============ 右侧：联系人详情面板 ============ -->
  <section class="contact-detail" :class="{ 'mobile-show': selectedId && isMobile }">
  <!-- 未选择联系人 -->
  <div v-if="!selectedContact" class="detail-empty">
  <div class="detail-empty-icon">
  <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
  </svg>
  </div>
  <p class="detail-empty-text">选择左侧联系人查看详情</p>
  <p class="detail-empty-hint">或点击「新增」添加新联系人</p>
  </div>

  <!-- 联系人详情 -->
  <div v-else class="detail-content">
  <!-- 手机端返回按钮（仅移动端显示） -->
  <button class="btn-back-mobile" @click="selectedId = null">
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="15 18 9 12 15 6"/>
  </svg>
  返回
  </button>
  <!-- 头部：渐变背景 + 头像 + 姓名 + 操作按钮 -->
  <div class="detail-header">
  <div class="header-banner" :style="{ background: `linear-gradient(135deg, ${getAvatarColor(selectedContact.name || primaryEmail(selectedContact))}22, transparent)` }"></div>
  <div class="header-inner">
  <div class="avatar-lg" :style="{ background: getAvatarColor(selectedContact.name || primaryEmail(selectedContact)) }">
  {{ avatarLetter(selectedContact) }}
  </div>
  <div class="header-info">
  <h2 class="detail-name">
  {{ selectedContact.name || '(未命名)' }}
  <button class="btn-icon-edit" @click="openEditDialog(selectedContact)" title="编辑联系人">
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
  </svg>
  </button>
  </h2>
  <div class="detail-meta">
  <span v-if="selectedContact.company" class="meta-tag meta-company">{{ selectedContact.company }}</span>
  <span v-if="selectedContact.group_name" class="meta-tag">{{ selectedContact.group_name }}</span>
  <span class="meta-email-count">{{ selectedContact.emails.length }} 个邮箱</span>
  </div>
  </div>
  <div class="header-actions">
  <button class="btn-action btn-delete" @click="handleDelete(selectedContact)" title="删除联系人">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
  </svg>
  <span class="btn-text">删除</span>
  </button>
  </div>
  </div>
  </div>

  <!-- 详情卡片区域：双列布局更饱满 -->
  <div class="detail-sections">
  <div class="sections-row">
  <!-- 邮箱列表（左列，较宽） -->
  <div class="detail-section">
  <div class="section-title">
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>
  </svg>
  邮箱地址
  </div>
  <div class="email-list">
  <div v-for="emailObj in selectedContact.emails" :key="emailObj.id" class="email-row">
  <span class="email-text">{{ emailObj.email }}</span>
  <span v-if="emailObj.is_primary" class="badge-primary">主</span>
  </div>
  </div>
  </div>

  <!-- 联系方式（右列） -->
  <div class="detail-section">
  <div class="section-title">
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>
  </svg>
  联系方式
  </div>
  <div class="info-list">
  <div class="info-item">
  <span class="info-label">电话</span>
  <span class="info-value">{{ selectedContact.phone || '—' }}</span>
  </div>
  <div class="info-item">
  <span class="info-label">工作单位</span>
  <span class="info-value">{{ selectedContact.company || '—' }}</span>
  </div>
  <div class="info-item">
  <span class="info-label">分组</span>
  <span class="info-value">{{ selectedContact.group_name || '—' }}</span>
  </div>
  </div>
  </div>
  </div>

  <!-- 往来邮件统计（全宽） -->
  <div class="detail-section">
  <div class="section-title">
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M3 3v18h18"/><path d="M18.7 8l-5.1 5.2-2.8-2.7L7 14.3"/>
  </svg>
  往来邮件
  </div>
  <div class="stats-grid">
  <!-- 统计加载中 -->
  <div v-if="statsLoading" class="stats-loading">
  <div class="spinner-sm"></div>
  <span>统计中...</span>
  </div>
  <template v-else>
  <div class="stats-card">
  <div class="stats-value">{{ statsData.count }}</div>
  <div class="stats-label">往来邮件总数</div>
  </div>
  <div class="stats-card">
  <div class="stats-value">{{ statsData.last_date ? formatRelativeDate(statsData.last_date) : '—' }}</div>
  <div class="stats-label">最近一次联系</div>
  </div>
  </template>
  </div>
  </div>

  <!-- 备注（全宽） -->
  <div v-if="selectedContact.remark" class="detail-section">
  <div class="section-title">
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
  </svg>
  备注
  </div>
  <div class="remark-box">{{ selectedContact.remark }}</div>
  </div>
  </div>
  </div>
  </section>

  <!-- ============ 新增/编辑弹窗 ============ -->
  <transition name="fade">
  <div v-if="showDialog" class="dialog-backdrop" @click.self="closeDialog">
  <div class="dialog">
  <h3 class="dialog-title">{{ editingContact ? '编辑联系人' : '新增联系人' }}</h3>
  <div class="dialog-body">
  <!-- 姓名 -->
  <div class="form-row">
  <label>姓名</label>
  <input v-model="formData.name" placeholder="联系人姓名（允许同名）" class="form-input" />
  </div>
  <!-- 多邮箱输入 -->
  <div class="form-row">
  <label>邮箱 *</label>
  <div class="email-input-list">
  <div v-for="(emailItem, idx) in formData.emails" :key="idx" class="email-input-row">
  <input
  v-model="emailItem.value"
  placeholder="邮箱地址"
  class="form-input"
  :class="{ error: emailErrors[idx] }"
  @input="emailErrors[idx] = ''"
  />
  <button v-if="formData.emails.length > 1" class="btn-remove-email" @click="removeEmailField(idx)" title="移除">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
  </button>
  <span v-if="emailErrors[idx]" class="form-error">{{ emailErrors[idx] }}</span>
  </div>
  </div>
  <button class="btn-add-email" @click="addEmailField">
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
  <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
  </svg>
  添加邮箱
  </button>
  </div>
  <!-- 电话 -->
  <div class="form-row">
  <label>电话</label>
  <input v-model="formData.phone" placeholder="联系电话（选填）" class="form-input" />
  </div>
  <!-- 工作单位 -->
  <div class="form-row">
  <label>工作单位</label>
  <input v-model="formData.company" placeholder="工作单位（选填）" class="form-input" />
  </div>
  <!-- 分组 -->
  <div class="form-row">
  <label>分组</label>
  <input v-model="formData.group_name" placeholder="分组名（选填）" class="form-input" />
  </div>
  <!-- 备注 -->
  <div class="form-row">
  <label>备注</label>
  <textarea v-model="formData.remark" placeholder="备注信息（选填）" class="form-textarea" rows="3"></textarea>
  </div>
  </div>
  <div class="dialog-footer">
  <button class="btn btn-cancel" @click="closeDialog">取消</button>
  <button class="btn btn-save" @click="handleSave" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
  </div>
  </div>
  </div>
  </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useContacts, type ContactItem, type ContactStats } from '../composables/useContacts';
import { useUIStore } from '../stores/ui';
import { getAvatarColor } from '../utils/mail-helpers';

const ui = useUIStore();
const { contacts, loading, loadContacts, addContact, editContact, removeContact, getContactStats } = useContacts();

// ============ 状态 ============
const searchKeyword = ref('');
const selectedId = ref<number | null>(null);
const showDialog = ref(false);
const editingContact = ref<ContactItem | null>(null);
const saving = ref(false);
const isMobile = ref(window.innerWidth < 768);

// 往来邮件统计
const statsData = ref<ContactStats>({ count: 0, last_date: '' });
const statsLoading = ref(false);

// 表单数据（多邮箱输入）
const formData = ref({
  name: '',
  emails: [{ value: '' }] as { value: string }[],
  phone: '',
  company: '',
  remark: '',
  group_name: '',
});
const emailErrors = ref<string[]>([]);

// ============ 计算属性 ============
/** 前端实时过滤（数据量不大，无需调 API） */
const filteredContacts = computed(() => {
  const kw = searchKeyword.value.trim().toLowerCase();
  if (!kw) return contacts.value;
  return contacts.value.filter(c => {
  const nameMatch = c.name.toLowerCase().includes(kw);
  const emailMatch = c.emails.some(e => e.email.toLowerCase().includes(kw));
  return nameMatch || emailMatch;
  });
});

/** 当前选中的联系人 */
const selectedContact = computed(() => {
  if (selectedId.value === null) return null;
  return contacts.value.find(c => c.id === selectedId.value) || null;
});

// ============ 工具函数 ============
/** 获取主邮箱，无主邮箱时取第一个 */
function primaryEmail(contact: ContactItem): string {
  const primary = contact.emails.find(e => e.is_primary);
  return primary?.email || contact.emails[0]?.email || '';
}

/** 获取头像字母（姓名首字或邮箱首字） */
function avatarLetter(contact: ContactItem): string {
  const source = contact.name || primaryEmail(contact);
  return source[0]?.toUpperCase() || '?';
}

/** 格式化为相对日期（今天/昨天/N天前/N周前），用于联系人统计展示 */
function formatRelativeDate(dateStr: string): string {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return '今天';
  if (days === 1) return '昨天';
  if (days < 7) return `${days} 天前`;
  if (days < 30) return `${Math.floor(days / 7)} 周前`;
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

// ============ 列表交互 ============
/** 选中联系人 */
function selectContact(id: number) {
  selectedId.value = id;
}

/** 监听选中联系人变化，加载往来邮件统计 */
watch(selectedContact, async () => {
  if (!selectedContact.value) {
  statsData.value = { count: 0, last_date: '' };
  return;
  }
  const email = primaryEmail(selectedContact.value);
  if (!email) return;
  statsLoading.value = true;
  try {
  statsData.value = await getContactStats(selectedContact.value.id, email);
  } catch {
  statsData.value = { count: 0, last_date: '' };
  } finally {
  statsLoading.value = false;
  }
});

// ============ 弹窗操作 ============
/** 打开新增弹窗 */
function openAddDialog() {
  editingContact.value = null;
  formData.value = {
  name: '',
  emails: [{ value: '' }],
  phone: '',
  company: '',
  remark: '',
  group_name: '',
  };
  emailErrors.value = [];
  showDialog.value = true;
}

/** 打开编辑弹窗 */
function openEditDialog(contact: ContactItem) {
  editingContact.value = contact;
  // 将 emails 数组转为可编辑的输入项
  const emailItems = contact.emails.length > 0
  ? contact.emails.map(e => ({ value: e.email }))
  : [{ value: '' }];
  formData.value = {
  name: contact.name,
  emails: emailItems,
  phone: contact.phone,
  company: contact.company,
  remark: contact.remark,
  group_name: contact.group_name,
  };
  emailErrors.value = [];
  showDialog.value = true;
}

/** 关闭弹窗 */
function closeDialog() {
  showDialog.value = false;
  editingContact.value = null;
  emailErrors.value = [];
}

/** 添加邮箱输入项 */
function addEmailField() {
  formData.value.emails.push({ value: '' });
}

/** 移除邮箱输入项 */
function removeEmailField(idx: number) {
  formData.value.emails.splice(idx, 1);
  emailErrors.value.splice(idx, 1);
}

/** 邮箱格式校验 */
function validateEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

/** 保存联系人（新增或编辑） */
async function handleSave() {
  // 收集并校验邮箱
  const emails = formData.value.emails.map(e => e.value.trim()).filter(e => e);
  emailErrors.value = formData.value.emails.map(e => {
  const val = e.value.trim();
  if (!val) return '';
  return validateEmail(val) ? '' : '邮箱格式不正确';
  });

  if (emails.length === 0) {
  ui.error('至少需要填写一个邮箱');
  return;
  }
  if (emailErrors.value.some(e => e)) {
  return;
  }
  // 检查邮箱是否重复
  const uniqueEmails = new Set(emails);
  if (uniqueEmails.size !== emails.length) {
  ui.error('存在重复的邮箱地址');
  return;
  }

  saving.value = true;
  try {
  const data = {
  name: formData.value.name.trim(),
  emails,
  phone: formData.value.phone.trim(),
  company: formData.value.company.trim(),
  remark: formData.value.remark.trim(),
  group_name: formData.value.group_name.trim(),
  };
  if (editingContact.value) {
  await editContact(editingContact.value.id, data);
  ui.success('联系人已更新');
  } else {
  await addContact(data);
  ui.success('联系人已添加');
  }
  showDialog.value = false;
  await loadContacts();
  } catch (e: any) {
  const msg = e?.response?.data?.error || e?.message || '';
  ui.error(msg || '保存失败');
  } finally {
  saving.value = false;
  }
}

/** 删除联系人 */
async function handleDelete(contact: ContactItem) {
  if (!confirm(`确定删除联系人「${contact.name || primaryEmail(contact)}」吗？`)) return;
  try {
  await removeContact(contact.id);
  ui.success('联系人已删除');
  // 清空选中状态
  if (selectedId.value === contact.id) {
  selectedId.value = null;
  }
  await loadContacts();
  } catch (e: any) {
  ui.error(e?.response?.data?.error || '删除失败');
  }
}

// ============ 响应式监听 ============
/** 窗口大小变化时更新移动端标识 */
function handleResize() {
  isMobile.value = window.innerWidth < 768;
}

// ============ 初始化 ============
onMounted(() => {
  loadContacts();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
});
</script>

<style scoped>
.contact-page {
  display: flex;
  height: 100%;
  background: var(--bg-secondary);
  overflow: hidden;
}

/* ============ 左侧侧边栏 ============ */
.contact-sidebar {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  border-right: 1px solid var(--border-color);
}

.sidebar-header {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid var(--border-color);
  align-items: center;
}

.search-box {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
}

.search-box svg {
  position: absolute;
  left: 10px;
  color: var(--text-secondary);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 7px 12px 7px 34px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  font-size: 13px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  outline: none;
  transition: border-color 0.2s, background 0.2s;
}

.search-input:focus {
  border-color: var(--color-accent);
  background: var(--bg-primary);
}

/* 新增按钮 - 始终显示蓝色 */
.btn-add {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 7px 12px;
  border: none;
  border-radius: 8px;
  background: var(--color-accent);
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.2s;
}

.btn-add:hover {
  background: var(--color-accent-hover);
}

.btn-add:active {
  transform: scale(0.97);
}

/* ============ 加载/空状态 ============ */
.state-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 60px 20px;
  color: var(--text-secondary);
  font-size: 13px;
}

.state-box.empty {
  text-align: center;
}

.empty-icon {
  margin-bottom: 12px;
  opacity: 0.4;
  color: var(--text-tertiary);
}

.state-title {
  font-size: 14px;
  margin: 0 0 4px;
  color: var(--text-primary);
}

.state-desc {
  font-size: 12px;
  margin: 0;
  color: var(--text-tertiary);
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--border-color);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.spinner-sm {
  width: 14px;
  height: 14px;
  border: 2px solid var(--border-color);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ============ 联系人列表 ============ */
.contact-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px;
}

.contact-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}

.contact-item:hover {
  background: var(--bg-hover);
}

.contact-item.active {
  background: var(--bg-active);
}

.avatar-sm {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-email {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 2px;
}

.email-count {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 10px;
  flex-shrink: 0;
}

.contact-item.active .email-count {
  background: var(--color-accent-light);
  color: var(--color-accent);
}

/* ============ 右侧详情面板 ============ */
.contact-detail {
  flex: 1;
  overflow-y: auto;
  background: var(--bg-secondary);
  position: relative;
}

/* 未选择状态 */
.detail-empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.detail-empty-icon {
  color: var(--text-tertiary);
  opacity: 0.5;
  margin-bottom: 8px;
}

.detail-empty-text {
  font-size: 15px;
  color: var(--text-secondary);
  margin: 0;
}

.detail-empty-hint {
  font-size: 13px;
  color: var(--text-tertiary);
  margin: 0;
}

/* 详情内容 */
.detail-content {
  max-width: 960px;
  margin: 0 auto;
  padding: 28px 36px;
}

/* 手机端返回按钮 - 桌面端隐藏，移动端显示 */
.btn-back-mobile {
  display: none;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  margin-bottom: 12px;
  border: none;
  border-radius: 8px;
  background: var(--bg-hover);
  color: var(--text-primary);
  font-size: 14px;
  cursor: pointer;
}

/* 头部：渐变背景 + 头像 + 姓名 + 操作 */
.detail-header {
  position: relative;
  padding: 20px 4px;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 24px;
  border-radius: 14px;
  overflow: hidden;
}

/* 头部渐变背景层 */
.header-banner {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.header-inner {
  position: relative;
  display: flex;
  align-items: center;
  gap: 20px;
}

.avatar-lg {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 28px;
  font-weight: 600;
  flex-shrink: 0;
  box-shadow: var(--shadow-md);
}

.header-info {
  flex: 1;
  min-width: 0;
}

.detail-name {
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 6px;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 名称后方的编辑图标按钮（类似邮件详情的加入联系人按钮） */
.btn-icon-edit {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  flex-shrink: 0;
}

.btn-icon-edit:hover {
  background: var(--bg-hover);
  color: var(--color-accent);
}

.detail-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.meta-tag {
  background: var(--color-accent-light);
  color: var(--color-accent);
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
}

/* 工作单位标签 - 绿色系，区别于分组 */
.meta-company {
  background: var(--color-success-light);
  color: var(--color-success);
}

.meta-email-count {
  font-size: 12px;
  color: var(--text-secondary);
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

/* 操作按钮 - 始终显示颜色 */
.btn-action {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 7px 14px;
  border: 1px solid transparent;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}

.btn-delete {
  background: var(--color-danger-light);
  color: var(--color-danger);
  border-color: transparent;
}

.btn-delete:hover {
  background: var(--color-danger);
  color: #fff;
}

/* ============ 详情区块 ============ */
.detail-sections {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 双列布局：邮箱地址 + 联系方式 并排显示 */
.sections-row {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 16px;
}

.detail-section {
  background: var(--bg-primary);
  border-radius: 12px;
  padding: 18px 20px;
  box-shadow: var(--shadow-sm);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 14px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.section-title svg {
  color: var(--text-tertiary);
}

/* 邮箱列表 */
.email-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.email-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
}

.email-text {
  font-size: 14px;
  color: var(--text-primary);
  word-break: break-all;
}

.badge-primary {
  background: var(--color-success-light);
  color: var(--color-success);
  font-size: 11px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
}

/* 联系方式列表（垂直排列） */
.info-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.info-label {
  font-size: 12px;
  color: var(--text-tertiary);
}

.info-value {
  font-size: 14px;
  color: var(--text-primary);
}

/* 统计卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.stats-card {
  background: var(--bg-secondary);
  border-radius: 10px;
  padding: 16px;
  text-align: center;
}

.stats-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--color-accent);
  margin-bottom: 4px;
}

.stats-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.stats-loading {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  color: var(--text-secondary);
  font-size: 13px;
}

/* 备注 */
.remark-box {
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.6;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 8px;
  white-space: pre-wrap;
}

/* ============ 弹窗 ============ */
.dialog-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  background: var(--bg-primary);
  border-radius: 14px;
  width: 90%;
  max-width: 480px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-xl);
}

.dialog-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  padding: 20px 24px 16px;
  border-bottom: 1px solid var(--border-color);
}

.dialog-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.form-row {
  margin-bottom: 16px;
}

.form-row label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.form-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  font-size: 14px;
  background: var(--bg-primary);
  color: var(--text-primary);
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.form-input:focus {
  border-color: var(--color-accent);
}

.form-input.error {
  border-color: var(--color-danger);
}

.form-textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  font-size: 14px;
  background: var(--bg-primary);
  color: var(--text-primary);
  outline: none;
  transition: border-color 0.2s;
  resize: vertical;
  font-family: inherit;
  box-sizing: border-box;
}

.form-textarea:focus {
  border-color: var(--color-accent);
}

.form-error {
  display: block;
  font-size: 12px;
  color: var(--color-danger);
  margin-top: 4px;
}

/* 多邮箱输入 */
.email-input-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 8px;
}

.email-input-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.email-input-row .form-input {
  flex: 1;
}

.btn-remove-email {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 6px;
  background: var(--color-danger-light);
  color: var(--color-danger);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.15s;
}

.btn-remove-email:hover {
  background: var(--color-danger);
  color: #fff;
}

.btn-add-email {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border: 1px dashed var(--border-color-strong);
  border-radius: 6px;
  background: transparent;
  color: var(--color-accent);
  font-size: 12px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.btn-add-email:hover {
  border-color: var(--color-accent);
  background: var(--color-accent-lighter);
}

/* 弹窗底部按钮 */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px 24px 20px;
  border-top: 1px solid var(--border-color);
}

.btn {
  padding: 8px 18px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 取消按钮 - 始终显示灰色 */
.btn-cancel {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn-cancel:hover {
  background: var(--border-color-strong);
}

/* 保存按钮 - 始终显示蓝色 */
.btn-save {
  background: var(--color-accent);
  color: #fff;
}

.btn-save:hover {
  background: var(--color-accent-hover);
}

/* ============ 过渡动画 ============ */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ============ 移动端响应式 ============ */
@media (max-width: 767px) {
  .contact-page {
  position: relative;
  }

  .contact-sidebar {
  width: 100%;
  position: absolute;
  inset: 0;
  z-index: 1;
  transition: transform 0.25s ease;
  }

  .contact-sidebar.mobile-hidden {
  transform: translateX(-100%);
  }

  .contact-detail {
  position: absolute;
  inset: 0;
  z-index: 2;
  transform: translateX(100%);
  transition: transform 0.25s ease;
  }

  .contact-detail.mobile-show {
  transform: translateX(0);
  }

  .detail-content {
  padding: 20px 16px;
  }

  /* 手机端显示返回按钮 */
  .btn-back-mobile {
  display: inline-flex;
  }

  .detail-header {
  flex-wrap: wrap;
  gap: 12px;
  }

  .avatar-lg {
  width: 56px;
  height: 56px;
  font-size: 22px;
  }

  .detail-name {
  font-size: 18px;
  }

  /* 删除按钮：不占满整行，靠右对齐与头像姓名同一行 */
  .header-actions {
  flex-shrink: 0;
  }

  /* 移动端删除按钮只显示图标，隐藏文字 */
  .btn-delete .btn-text {
  display: none;
  }
  .btn-delete {
  padding: 7px 9px;
  }

  /* 邮箱数量文字不换行，避免纵向分布 */
  .detail-meta {
  flex-wrap: nowrap;
  overflow: hidden;
  white-space: nowrap;
  }
  .meta-email-count {
  flex-shrink: 0;
  }

  .stats-grid,
  .sections-row {
  grid-template-columns: 1fr;
  }
}
</style>
