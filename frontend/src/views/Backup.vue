<template>
  <div class="backup-page">
  <!-- 主体：账号tabs + 列表 + 详情（文件夹由侧边栏 backupStore 管理） -->
  <div class="backup-content">
  <!-- 顶部：账号切换 tabs -->
  <div class="backup-toolbar">
  <div class="account-tabs">
  <!-- 各邮箱平台（无"全部"选项，必须选择具体账号） -->
  <button
  v-for="acc in accounts"
  :key="acc.account_id"
  class="account-tab"
  :class="{ active: selectedAccount === acc.account_id }"
  @click="switchAccount(acc.account_id)"
  >
  <span class="account-icon" v-html="providerIcon(acc.provider)"></span>
  <span class="account-email">{{ acc.email }}</span>
  <span class="account-count">{{ acc.count }}</span>
  </button>
  </div>
  </div>

  <!-- 邮件列表视图（未选中邮件时显示） -->
  <div v-if="!selectedMessage" class="archive-list">
  <!-- 筛选栏：文件夹名+数量 | 全部/存活/已删除 | 立即备份（参照 MailList 风格） -->
  <div v-if="accounts.length > 0" class="list-toolbar">
  <div class="toolbar-left">
  <!-- 移动端：iOS风格文件夹选择器 -->
  <button v-if="isMobile" class="folder-picker" @click="showFolderSheet = true">
  <span class="picker-label">{{ currentFolderName }}</span>
  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="6 9 12 15 18 9"/></svg>
  </button>
  <!-- 桌面端：文件夹名+数量 -->
  <span v-else class="list-count">{{ currentFolderName }} · {{ total }}封</span>
  <span class="toolbar-divider"></span>
  <!-- 桌面端：内联筛选按钮 -->
  <template v-if="!isMobile">
  <button class="filter-btn" :class="{ active: filterDeleted === '' }" @click="setFilterDeleted('')">全部 {{ currentFolderStats.count }}</button>
  <button class="filter-btn" :class="{ active: filterDeleted === 'alive' }" @click="setFilterDeleted('alive')">存活 {{ currentFolderStats.alive }}</button>
  <button class="filter-btn" :class="{ active: filterDeleted === 'deleted' }" @click="setFilterDeleted('deleted')">已删除 {{ currentFolderStats.deleted }}</button>
  </template>
  </div>
  <div class="toolbar-right">
  <!-- 移动端：筛选展开/收起按钮 -->
  <button v-if="isMobile" class="btn-icon mobile-filter-toggle" :class="{ active: filterDeleted !== '' }" @click="showMobileFilters = !showMobileFilters">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>
  </button>
  <!-- 立即备份：图标按钮风格，与 MailList 的 rebuild-btn 一致 -->
  <button class="btn-icon backup-icon-btn" @click="triggerBackup" :disabled="backingUp || !selectedAccount" :title="selectedAccount ? '备份当前邮箱' : '请先选择邮箱'">
  <svg v-if="!backingUp" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
  </svg>
  <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="spin-icon">
  <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
  </svg>
  </button>
  </div>
  <!-- 移动端：筛选下拉菜单 -->
  <transition name="filter-dropdown">
  <div v-if="showMobileFilters" class="mobile-filter-dropdown">
  <div class="filter-backdrop" @click="showMobileFilters = false"></div>
  <div class="filter-dropdown-menu filter-dropdown-compact">
  <button class="filter-dropdown-item" :class="{ active: filterDeleted === '' }" @click="setFilterDeleted(''); showMobileFilters = false">全部 {{ currentFolderStats.count }}</button>
  <button class="filter-dropdown-item" :class="{ active: filterDeleted === 'alive' }" @click="setFilterDeleted('alive'); showMobileFilters = false">存活 {{ currentFolderStats.alive }}</button>
  <button class="filter-dropdown-item" :class="{ active: filterDeleted === 'deleted' }" @click="setFilterDeleted('deleted'); showMobileFilters = false">已删除 {{ currentFolderStats.deleted }}</button>
  </div>
  </div>
  </transition>
  </div>

  <!-- iOS风格底部弹出文件夹选择（移动端） -->
  <transition name="sheet">
  <div v-if="showFolderSheet" class="sheet-backdrop" @click.self="showFolderSheet = false">
  <div class="sheet-content">
  <div class="sheet-handle"></div>
  <div class="sheet-title">文件夹</div>
  <div class="sheet-list">
  <button
  v-for="f in backupStore.folders"
  :key="f.folder"
  class="sheet-item"
  :class="{ active: backupStore.currentFolder === f.folder }"
  @click="selectBackupFolder(f.folder); showFolderSheet = false"
  >
  <span class="sheet-folder-name">{{ backupStore.folderDisplayName(f.folder) }}</span>
  <span class="sheet-folder-count" v-if="f.count">{{ f.count }}</span>
  </button>
  </div>
  </div>
  </div>
  </transition>

  <!-- 未选择任何备份邮箱 -->
  <div v-if="accounts.length === 0" class="empty-state">
  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
  </svg>
  <p>暂无备份邮箱</p>
  <p class="empty-hint">请在设置中开启备份并选择需要备份的邮箱</p>
  </div>
  <div v-else-if="loading" class="loading-state">加载中...</div>
  <div v-else-if="messages.length === 0" class="empty-state">
  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
  </svg>
  <p>暂无备份邮件</p>
  <p class="empty-hint">点击右上角"立即备份"，将当前邮箱邮件归档到本地</p>
  </div>

  <!-- 列表项：单行水平布局，与 MailList 视觉一致 -->
  <button
  v-for="msg in messages"
  :key="`${msg.account_id}-${msg.folder}-${msg.uid}`"
  class="mail-item"
  @click="selectMessage(msg)"
  >
  <!-- 左列：头像 + 发件人 -->
  <div class="mail-sender">
  <div class="mail-avatar" :style="{ background: getAvatarColor(msg.from_addr) }">
  {{ getInitial(msg.from_addr) }}
  </div>
  <span class="mail-from">{{ displayName(msg.from_addr) }}</span>
  </div>
  <!-- 中列：主题 + 附件图标 + 服务器已删除标记 -->
  <div class="mail-info">
  <div class="mail-main-row">
  <span class="mail-subject">{{ msg.subject || '(无主题)' }}</span>
  <svg v-if="msg.has_attachments" class="att-badge" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/></svg>
  <span v-if="msg.is_deleted_on_server" class="deleted-tag">服务器已删除</span>
  </div>
  </div>
  <!-- 右列：日期 -->
  <span class="mail-date">{{ formatDate(msg.date) }}</span>
  </button>

  <!-- 分页 -->
  <div v-if="total > pageSize" class="pagination">
  <button :disabled="page <= 1" @click="changePage(page - 1)">上一页</button>
  <span class="page-info">{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
  <button :disabled="page * pageSize >= total" @click="changePage(page + 1)">下一页</button>
  </div>
  </div>

  <!-- 邮件详情视图（选中邮件后整个区域切换为详情，与 MailList 一致） -->
  <div v-else class="archive-detail">
  <!-- 顶部工具栏：返回按钮 + 打印按钮（风格与 MailList 详情页一致） -->
  <div class="detail-toolbar">
  <button class="btn-back" @click="backToList">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="15 18 9 12 15 6"/>
  </svg>
  <span>返回</span>
  </button>
  <div class="detail-actions">
  <button class="btn-action" @click="printMail" :disabled="printing" title="打印">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>
  </svg>
  <span>{{ printing ? '打印中...' : '打印' }}</span>
  </button>
  </div>
  </div>

  <!-- 滚动区域：标题 + 元信息 + 正文 + 附件 -->
  <div class="detail-body">
  <!-- 标题 + 发件人信息 -->
  <div class="detail-header">
  <!-- 主题 -->
  <h2 class="detail-subject">{{ selectedMessage.subject || '(无主题)' }}</h2>

  <!-- 第一行：头像 + 发件人姓名/邮箱 -->
  <div class="detail-sender-row">
  <div class="meta-avatar" :style="{ background: getAvatarColor(selectedMessage.from_addr) }">
  {{ getInitial(selectedMessage.from_addr) }}
  </div>
  <div class="meta-from">
  <span class="from-name">{{ displayName(selectedMessage.from_addr) }}</span>
  <span class="from-email" v-if="displayName(selectedMessage.from_addr) !== selectedMessage.from_addr">&lt;{{ selectedMessage.from_addr }}&gt;</span>
  </div>
  </div>

  <!-- 分割线 -->
  <div class="detail-divider"></div>

  <!-- 灰色信息卡：发件人 / 收件人 / 抄送 / 时间（全宽，优先用详情数据） -->
  <div class="meta-card">
  <div class="meta-row">
  <span class="meta-row-label">发件人</span>
  <span class="meta-row-value" :title="metaFrom">{{ formatAddressList(metaFrom) }}</span>
  </div>
  <div class="meta-row" v-if="metaTo">
  <span class="meta-row-label">收件人</span>
  <span class="meta-row-value" :title="metaTo">{{ formatAddressList(metaTo) }}</span>
  </div>
  <div class="meta-row" v-if="metaCc">
  <span class="meta-row-label">抄送</span>
  <span class="meta-row-value" :title="metaCc">{{ formatAddressList(metaCc) }}</span>
  </div>
  <div class="meta-row">
  <span class="meta-row-label">时间</span>
  <span class="meta-row-value">{{ formatDetailDate(selectedMessage.date) }}</span>
  </div>
  </div>

  <!-- 备份特有信息：本地备份提示 + 归档信息 -->
  <div class="backup-info">
  <div class="backup-notice">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
  </svg>
  <span>您正在查看本地备份</span>
  <span v-if="detailData?.is_deleted_on_server" class="deleted-notice">· 此邮件已从服务器删除</span>
  </div>
  <div class="archive-meta">
  <span v-if="selectedMessage.size">大小 {{ formatSize(selectedMessage.size) }}</span>
  <span>归档于 {{ formatTimestamp(selectedMessage.archived_at) }}</span>
  </div>
  </div>

  <!-- 分割线（信息卡与正文之间） -->
  <div class="detail-divider"></div>
  </div>

  <!-- 正文 -->
  <div v-if="detailLoading" class="body-skeleton">
  <div class="skeleton-line" style="width: 90%"></div>
  <div class="skeleton-line" style="width: 100%"></div>
  <div class="skeleton-line" style="width: 75%"></div>
  <div class="skeleton-line" style="width: 95%"></div>
  <div class="skeleton-line" style="width: 60%"></div>
  </div>
  <template v-else-if="detailData">
  <!-- 与 MailList 一致：同页 v-html 渲染，避免飞牛 WebView 对 srcdoc iframe 空白 -->
  <div
  v-if="detailData.body_html || detailData.body_text"
  class="detail-content"
  v-html="renderMailBody(detailData.body_html, detailData.body_text)"
  @click="handleMailLinkClick"
  ></div>
  <div v-else class="body-empty">（无正文内容）</div>

  <!-- 附件列表 -->
  <div v-if="detailData.attachments && detailData.attachments.length > 0" class="attachment-list">
  <div class="attachment-header">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/></svg>
  <span>附件 ({{ detailData.attachments.length }})</span>
  </div>
  <div v-for="(att, i) in detailData.attachments" :key="i" class="attachment-item" @click="downloadAttachment(att)">
  <div class="att-icon">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
  </div>
  <div class="att-info">
  <div class="att-name">{{ att.filename || '(未命名)' }}</div>
  <div class="att-meta">{{ formatSize(att.size) }}</div>
  </div>
  <div class="att-download">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
  </div>
  </div>
  </div>
  </template>
  </div>
  </div>
  </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import api from '../utils/api';
import { renderMailBody, handleMailLinkClick } from '../utils/sanitize';
import { providerIcon } from '../utils/provider';
import { useBackupStore } from '../stores/backup';
import { useUIStore } from '../stores/ui';
import { exportMailToPDF } from '../utils/export-pdf';
import { getInitial, getAvatarColor, formatDate, formatDetailDate, formatFileSize, formatAddressList, downloadAttachment as downloadAttachmentFile } from '../utils/mail-helpers';
// 联系人姓名匹配：与 MailList/UnifiedInbox 共享同一份映射表（模块级单例）
import { useContactNameMap } from '../composables/useContactNameMap';
import type { ArchivedMessage, ArchivedMessageDetail, BackupAttachment, BackupStatus } from '../types/mail';

// ==================== Store ====================

const backupStore = useBackupStore();
const uiStore = useUIStore();

// ==================== 状态 ====================

const loading = ref(false);
const messages = ref<ArchivedMessage[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(40);
const accounts = ref<BackupStatus['accounts']>([]);

// 筛选状态：文件夹来自 backupStore（侧边栏选中），账号和删除筛选为本地状态
const selectedAccount = ref('');
const filterDeleted = ref('');

// 详情状态
const selectedMessage = ref<ArchivedMessage | null>(null);
const detailData = ref<ArchivedMessageDetail | null>(null);
const detailLoading = ref(false);

// UI 状态
const backingUp = ref(false);

// 移动端状态
const isMobile = ref(window.innerWidth <= 768);
const showFolderSheet = ref(false);  // 底部弹出文件夹选择
const showMobileFilters = ref(false);  // 移动端筛选下拉
const printing = ref(false);

// ==================== 计算属性 ====================

/** 当前文件夹显示名（用于筛选栏左侧"文件夹名 · X封"） */
const currentFolderName = computed(() => {
  return backupStore.folderDisplayName(backupStore.currentFolder);
});

/** 当前文件夹的筛选统计（全部/存活/已删除数量） */
const currentFolderStats = computed(() => {
  const f = backupStore.folders.find(f => f.folder === backupStore.currentFolder);
  const count = f?.count || 0;
  const deleted = f?.deleted_count || 0;
  return { count, alive: count - deleted, deleted };
});

// ==================== 详情页 meta 信息（优先用详情数据，列表数据兜底） ====================

const metaFrom = computed(() => detailData.value?.from_addr || selectedMessage.value?.from_addr || '');
const metaTo = computed(() => detailData.value?.to_addr || selectedMessage.value?.to_addr || '');
const metaCc = computed(() => detailData.value?.cc || selectedMessage.value?.cc || '');

// ==================== 生命周期 ====================

onMounted(async () => {
  await loadStatus();
  // 加载联系人映射表（模块级单例，已加载则跳过，不重复请求）
  loadContactMap();
  // 默认选中第一个账号（无"全部"选项，必须选择具体账号）
  if (accounts.value.length > 0) {
  await switchAccount(accounts.value[0].account_id);
  }
  // 移动端窗口尺寸监听
  window.addEventListener('resize', onResize);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize);
});

// 窗口尺寸变化时更新 isMobile
let resizeTimer: ReturnType<typeof setTimeout> | null = null;
function onResize() {
  if (resizeTimer) clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => { isMobile.value = window.innerWidth <= 768; }, 150);
}

/** 选择备份文件夹（移动端底部弹出菜单调用） */
function selectBackupFolder(folder: string) {
  backupStore.setFolder(folder);
}

// 监听侧边栏文件夹切换 → 重新加载列表
watch(() => backupStore.currentFolder, () => {
  page.value = 1;
  loadList();
});

// ==================== 数据加载 ====================

/** 加载备份状态（统计信息 + 账号列表） */
async function loadStatus() {
  try {
  const data = await api.get('/backup/status') as any;
  accounts.value = data.accounts || [];
  } catch (e) {
  console.error('加载备份状态失败:', e);
  }
}

/** 加载归档邮件列表（使用 backupStore.currentFolder 作为文件夹筛选） */
async function loadList() {
  loading.value = true;
  try {
  const params: Record<string, any> = {
  page: page.value,
  page_size: pageSize.value,
  };
  if (selectedAccount.value) params.account_id = selectedAccount.value;
  // 文件夹来自 store（侧边栏选中）
  if (backupStore.currentFolder) params.folder = backupStore.currentFolder;
  if (filterDeleted.value) params.deleted_filter = filterDeleted.value;

  const data = await api.get('/backup/messages', { params }) as any;
  messages.value = data.messages || [];
  total.value = data.total || 0;
  } catch (e) {
  console.error('加载归档列表失败:', e);
  uiStore.error('加载归档列表失败');
  } finally {
  loading.value = false;
  }
}

/** 选中邮件，加载详情 */
async function selectMessage(msg: ArchivedMessage) {
  selectedMessage.value = msg;
  detailData.value = null;
  detailLoading.value = true;
  try {
  const data = await api.get(
  `/backup/messages/${msg.account_id}/${encodeURIComponent(msg.folder)}/${msg.uid}`
  ) as any;
  detailData.value = data;
  } catch (e: any) {
  uiStore.error(e.message || '加载详情失败');
  } finally {
  detailLoading.value = false;
  }
}

// ==================== 操作 ====================

/** 设置删除状态筛选（全部/存活/已删除），重置页码并重新加载列表 */
function setFilterDeleted(value: string) {
  filterDeleted.value = value;
  page.value = 1;
  loadList();
}

/** 切换账号：更新 tabs 高亮 + 加载该账号文件夹统计 + 加载列表 */
async function switchAccount(accountId: string) {
  selectedAccount.value = accountId;
  page.value = 1;
  // 加载该账号的文件夹统计（5个核心文件夹固定，只是更新计数）
  await backupStore.loadFolders(accountId);
  // currentFolder 默认是 INBOX，一定在5个核心文件夹中，直接加载列表
  loadList();
}

/** 触发全量备份 */
async function triggerBackup() {
  if (!selectedAccount.value) {
  uiStore.error('请先选择要备份的邮箱');
  return;
  }
  backingUp.value = true;
  try {
  // 仅备份当前选中的邮箱（account_id 参数）
  const data = await api.post('/backup/run', null, { params: { account_id: selectedAccount.value } }) as any;
  if (data.success) {
  uiStore.success('备份任务已启动，请稍后刷新查看');
  setTimeout(() => { loadStatus(); backupStore.loadFolders(selectedAccount.value); loadList(); }, 3000);
  } else {
  uiStore.error(data.message || '备份启动失败');
  }
  } catch (e: any) {
  uiStore.error(e.message || '备份启动失败');
  } finally {
  backingUp.value = false;
  }
}

/** 翻页 */
function changePage(newPage: number) {
  page.value = newPage;
  loadList();
}

/** 返回列表（清空选中状态和详情数据） */
function backToList() {
  selectedMessage.value = null;
  detailData.value = null;
}

/** 打印当前邮件（通过 iframe + window.print() 导出 PDF） */
async function printMail() {
  if (!detailData.value || printing.value) return;
  printing.value = true;
  try {
  // ArchivedMessageDetail 与 Message 字段兼容，用 as any 转换
  await exportMailToPDF(detailData.value as any);
  } catch (e: any) {
  console.error('打印失败:', e);
  uiStore.error(e?.message || '打印失败');
  } finally {
  printing.value = false;
  }
}

// ==================== 工具函数 ====================

// 联系人姓名匹配：优先返回联系人姓名，未命中则用 extractName 逻辑
// 与 MailList/UnifiedInbox 共享同一份模块级映射表，避免重复请求
const { displayName, loadMap: loadContactMap } = useContactNameMap();

/** 格式化时间戳（归档时间，秒级时间戳） */
function formatTimestamp(ts: number): string {
  if (!ts) return '';
  return formatDate(new Date(ts * 1000).toISOString());
}

/** 格式化文件大小：复用共享工具函数 */
function formatSize(bytes: number): string {
  return formatFileSize(bytes) || '0 B';
}

/** 下载附件：复用公共工具函数，补备份邮件的上下文（uid 作为 messageId） */
function downloadAttachment(att: BackupAttachment) {
  const msg = selectedMessage.value;
  if (!msg) return;
  downloadAttachmentFile({
  messageId: String(msg.uid),
  accountId: msg.account_id,
  folder: msg.folder,
  partNumber: att.part_number,
  filename: att.filename || 'attachment',
  });
}
</script>

<style scoped>
.backup-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary, #f5f5f7);
}

/* ==================== 内容区 ==================== */
.backup-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ==================== 顶部工具栏（仅账号 tabs） ==================== */
.backup-toolbar {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  gap: 12px;
  flex-wrap: wrap;
  min-height: 48px;
}

/* 账号 tabs */
.account-tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  overflow-x: auto;
  scrollbar-width: none;
  flex: 1;
}

.account-tabs::-webkit-scrollbar { display: none; }

.account-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: none;
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-secondary, #86868b);
  transition: background 0.15s, color 0.15s;
  white-space: nowrap;
  flex-shrink: 0;
}

.account-tab:hover { background: rgba(0, 0, 0, 0.04); }
.account-tab.active {
  background: rgba(0, 122, 255, 0.1);
  color: #007aff;
  font-weight: 500;
}

.account-icon { display: flex; align-items: center; }
.account-icon svg { width: 16px; height: 16px; }

.account-email {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-count {
  font-size: 11px;
  background: rgba(0, 0, 0, 0.06);
  padding: 1px 6px;
  border-radius: 8px;
  color: var(--text-tertiary, #a1a1a6);
}

.account-tab.active .account-count {
  background: rgba(0, 122, 255, 0.15);
  color: #007aff;
}

/* ==================== 筛选栏（列表上方，参照 MailList 风格） ==================== */
.list-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 文件夹名+数量 */
.list-count {
  font-size: 12px;
  color: var(--text-tertiary, #a1a1a6);
  font-weight: 500;
  white-space: nowrap;
}

/* 分隔线 */
.toolbar-divider {
  width: 1px;
  height: 16px;
  background: rgba(0, 0, 0, 0.1);
  flex-shrink: 0;
  margin: 0 4px;
}

/* 筛选按钮（全部/存活/已删除） */
.filter-btn {
  padding: 3px 10px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--text-tertiary, #a1a1a6);
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.15s;
}
.filter-btn:hover {
  background: rgba(0, 0, 0, 0.04);
  color: var(--text-secondary, #86868b);
}
.filter-btn.active {
  background: rgba(0, 122, 255, 0.1);
  color: #007aff;
  font-weight: 500;
}

/* 立即备份图标按钮（与 MailList 的 rebuild-btn 风格一致） */
.btn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--text-secondary, #86868b);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.btn-icon:hover:not(:disabled) {
  background: var(--bg-hover, rgba(0, 0, 0, 0.05));
  color: var(--text-primary, #1d1d1f);
}

.btn-icon:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 备份中旋转动画 */
.spin-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ==================== 邮件列表 ==================== */
.archive-list {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-secondary, #86868b);
  gap: 8px;
}

.empty-state p { margin: 0; font-size: 14px; }
.empty-hint { font-size: 12px !important; opacity: 0.7; }

/* ==================== 邮件列表项（与 MailList 视觉一致） ==================== */
.mail-item {
  display: flex;
  align-items: center;
  gap: 0;
  padding: 10px 16px;
  border: none;
  background: transparent;
  border-bottom: 1px solid var(--border-color, rgba(0, 0, 0, 0.06));
  cursor: pointer;
  transition: background 0.15s;
  width: 100%;
  text-align: left;
  font-family: inherit;
  min-height: 52px;
}

.mail-item:hover { background: var(--bg-hover, rgba(0, 0, 0, 0.04)); }

/* 左列：头像 + 发件人（固定宽度，保证各行对齐） */
.mail-sender {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-shrink: 0;
  width: 160px;
  min-width: 0;
  padding-right: 12px;
}

.mail-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.mail-from {
  font-size: 13px;
  color: var(--text-secondary, #86868b);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
  flex: 1;
  min-width: 0;
}

/* 中列：主题 + 附件图标 + 服务器已删除标记 */
.mail-info {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
}

.mail-main-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
}

.mail-subject {
  font-size: 13px;
  color: var(--text-secondary, #86868b);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

/* 附件图标（回形针） */
.att-badge {
  flex-shrink: 0;
  color: var(--text-tertiary, #a1a1a6);
  margin-left: 2px;
}

/* 服务器已删除标记 */
.deleted-tag {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 500;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(255, 59, 48, 0.12);
  color: #ff3b30;
  white-space: nowrap;
}

/* 右列：日期（固定宽度，右对齐） */
.mail-date {
  font-size: 11px;
  color: var(--text-tertiary, #a1a1a6);
  flex-shrink: 0;
  white-space: nowrap;
  width: 64px;
  text-align: right;
}

/* ==================== 分页 ==================== */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 16px;
}

.pagination button {
  padding: 6px 14px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.8);
  font-size: 12px;
  cursor: pointer;
  color: var(--text-primary, #1d1d1f);
  transition: opacity 0.2s;
}

.pagination button:hover:not(:disabled) { background: rgba(255, 255, 255, 1); }
.pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
.page-info { font-size: 12px; color: var(--text-secondary, #86868b); }

/* ==================== 详情视图（占满整个区域，与 MailList 一致） ==================== */
.archive-detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.8);
  overflow: hidden;
}

/* 顶部工具栏：返回按钮 */
.detail-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border-color, rgba(0, 0, 0, 0.06));
  background: var(--bg-primary, rgba(255, 255, 255, 0.7));
  backdrop-filter: blur(20px);
  flex-shrink: 0;
}

.btn-back {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border: none;
  background: transparent;
  color: var(--accent-blue, #007aff);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.15s;
  font-family: inherit;
}

.btn-back:hover { background: var(--bg-hover, rgba(0, 0, 0, 0.04)); }

/* 详情页操作按钮容器（打印等） */
.detail-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 详情页操作按钮（图标+文字，风格与 MailList 一致） */
.btn-action {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: none;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.05);
  color: var(--text-secondary, #86868b);
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.15s;
}
.btn-action:hover {
  background: rgba(0, 0, 0, 0.08);
  color: var(--text-primary, #1d1d1f);
}
.btn-action:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 手机端：详情页工具栏按钮只显示图标，隐藏文字 */
@media (max-width: 768px) {
  .btn-back span,
  .btn-action span {
  display: none;
  }
}

/* 滚动区域 */
.detail-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

/* 标题 + 发件人信息 */
.detail-header {
  margin-bottom: 0;
}

.detail-subject {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary, #1d1d1f);
  margin: 0 0 16px 0;
  line-height: 1.4;
  word-break: break-word;
}

/* 第一行：头像 + 发件人姓名/邮箱 */
.detail-sender-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.meta-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 15px;
  font-weight: 600;
  flex-shrink: 0;
}

.meta-from {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
}

.from-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, #1d1d1f);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.from-email {
  font-size: 12px;
  color: var(--text-tertiary, #a1a1a6);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

/* 分割线：头像行 / 信息卡 / 正文 之间 */
.detail-divider {
  height: 1px;
  background: var(--border-color, rgba(0, 0, 0, 0.08));
  margin: 12px 0;
}

/* 邮件信息卡片：灰色背景，全宽 */
.meta-card {
  width: 100%;
  box-sizing: border-box;
  padding: 12px 14px;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.meta-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 12px;
  line-height: 1.6;
}
.meta-row-label {
  color: var(--text-tertiary, #a1a1a6);
  flex-shrink: 0;
  width: 48px;
  font-weight: 500;
}
.meta-row-value {
  color: var(--text-primary, #1d1d1f);
  word-break: break-all;
  flex: 1;
  min-width: 0;
}

/* 备份特有信息区：本地备份提示 + 归档元信息 */
.backup-info {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.backup-notice {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #ff9500;
}

.deleted-notice {
  color: #ff3b30;
  font-weight: 500;
  margin-left: 4px;
}

.archive-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11px;
  color: var(--text-tertiary, #a1a1a6);
}

/* 正文骨架屏 */
.body-skeleton {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 10px 0;
}

.skeleton-line {
  height: 14px;
  background: linear-gradient(90deg, rgba(0,0,0,0.04) 25%, rgba(0,0,0,0.08) 50%, rgba(0,0,0,0.04) 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.4s ease infinite;
  border-radius: 4px;
}

@keyframes skeleton-loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* 正文：与 MailList .detail-content 一致，同页渲染避免 iframe 兼容问题 */
.detail-content {
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-primary, #1d1d1f);
  word-break: break-word;
  overflow-wrap: anywhere;
}

.detail-content :deep(img) {
  max-width: 100%;
  height: auto;
}

.detail-content :deep(a) {
  color: #0071e3;
  word-break: break-all;
}

.detail-content :deep(table) {
  max-width: 100%;
  border-collapse: collapse;
}

.body-empty {
  color: var(--text-tertiary, #a1a1a6);
  font-size: 13px;
  text-align: center;
  padding: 40px;
}

/* 附件列表 */
.attachment-list {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color, rgba(0, 0, 0, 0.06));
}

.attachment-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, #1d1d1f);
  margin-bottom: 10px;
}

.attachment-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.03);
  margin-bottom: 6px;
  transition: background 0.15s;
}

.attachment-item:hover { background: rgba(0, 0, 0, 0.06); }

.att-icon {
  display: flex;
  align-items: center;
  color: var(--text-secondary, #86868b);
  flex-shrink: 0;
}

.att-info {
  flex: 1;
  min-width: 0;
}

.att-name {
  font-size: 13px;
  color: var(--text-primary, #1d1d1f);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.att-meta {
  font-size: 11px;
  color: var(--text-tertiary, #a1a1a6);
  margin-top: 2px;
}

/* 附件下载按钮：默认灰色，hover 时变蓝 */
.att-download {
  flex-shrink: 0;
  color: var(--text-tertiary, #999);
  padding: 4px;
  border-radius: 4px;
  transition: color 0.15s;
}
.attachment-item:hover .att-download {
  color: var(--primary, #007aff);
}

/* ==================== 移动端适配 ==================== */
.mobile-filter-toggle { display: none; }

@media (max-width: 768px) {
  .backup-toolbar { padding: 8px 12px; }
  .account-tab .account-email { max-width: 100px; }
  .detail-body { padding: 16px; }
  .detail-subject { font-size: 16px; }

  /* 移动端文件夹选择器按钮 */
  .folder-picker {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  border: none;
  border-radius: var(--radius-md, 8px);
  background: rgba(0, 122, 255, 0.1);
  color: var(--accent-blue, #007aff);
  font-size: 13px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  }

  /* 移动端筛选按钮显示 */
  .mobile-filter-toggle { display: flex; }
  .mobile-filter-toggle.active { color: var(--accent-blue, #007aff); }

  /* 工具栏作为下拉菜单的定位基准 */
  .list-toolbar { position: relative; }

  /* 移动端筛选下拉菜单 */
  .mobile-filter-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 100;
  }
  .filter-backdrop {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  pointer-events: auto;
  }
  .filter-dropdown-menu {
  position: relative;
  pointer-events: auto;
  background: var(--bg-primary, #fff);
  border-bottom: 1px solid var(--border-color, rgba(0,0,0,0.06));
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  }
  .filter-dropdown-compact { padding: 4px 0; }
  .filter-dropdown-item {
  display: flex;
  width: 100%;
  padding: 10px 16px;
  border: none;
  background: transparent;
  text-align: left;
  font-size: 14px;
  color: var(--text-primary, #1d1d1f);
  cursor: pointer;
  font-family: inherit;
  }
  .filter-dropdown-item.active { color: var(--accent-blue, #007aff); font-weight: 500; }

  /* iOS风格底部弹出文件夹选择 */
  .sheet-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  z-index: 1000;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  }
  .sheet-content {
  width: 100%;
  max-width: 420px;
  max-height: 60vh;
  background: #fff;
  border-radius: 14px 14px 0 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  }
  .sheet-handle {
  width: 36px;
  height: 5px;
  border-radius: 3px;
  background: #d1d1d6;
  margin: 8px auto 4px;
  }
  .sheet-title {
  padding: 8px 20px 12px;
  font-size: 13px;
  font-weight: 600;
  color: #8e8e93;
  text-align: center;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  }
  .sheet-list {
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding-bottom: env(safe-area-inset-bottom, 20px);
  }
  .sheet-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 13px 20px;
  border: none;
  background: #fff;
  font-size: 17px;
  color: var(--text-primary, #1d1d1f);
  text-align: left;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.15s;
  }
  .sheet-item:active { background: #f2f2f7; }
  .sheet-item.active { color: var(--accent-blue, #007aff); font-weight: 500; }
  .sheet-item + .sheet-item { border-top: 0.5px solid #e5e5ea; }
  .sheet-folder-name { flex: 1; }
  .sheet-folder-count { font-size: 15px; color: #8e8e93; margin-right: 8px; }

  /* 弹出层动画 */
  .sheet-enter-active, .sheet-leave-active { transition: all 0.3s ease; }
  .sheet-enter-from, .sheet-leave-to { opacity: 0; }
  .sheet-enter-from .sheet-content, .sheet-leave-to .sheet-content { transform: translateY(100%); }
  .sheet-enter-active .sheet-content, .sheet-leave-active .sheet-content { transition: transform 0.3s ease; }

  /* 筛选下拉动画 */
  .filter-dropdown-enter-active, .filter-dropdown-leave-active { transition: opacity 0.2s; }
  .filter-dropdown-enter-from, .filter-dropdown-leave-to { opacity: 0; }
}
</style>
