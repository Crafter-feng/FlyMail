<template>
  <div class="account-page">
  <!-- 操作栏 -->
  <div class="toolbar">
  <div class="sort-toggle">
  <button class="toggle-btn" :class="{ active: sortBy === 'group' }" @click="sortBy = 'group'">按分组</button>
  <button class="toggle-btn" :class="{ active: sortBy === 'platform' }" @click="sortBy = 'platform'">按平台</button>
  </div>
  <button class="btn btn-primary" @click="showAddDialog = true">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
  <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
  </svg>
  添加账号
  </button>
  </div>

  <!-- 加载状态 -->
  <div v-if="loading" class="loading-state">
  <div class="loading-dot"></div>
  <span>加载中...</span>
  </div>

  <!-- 空状态 -->
  <div v-else-if="mailStore.accounts.length === 0" class="empty-state">
  <div class="empty-icon">
  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2">
  <rect x="2" y="4" width="20" height="16" rx="2"/>
  <path d="M22 4L12 13L2 4"/>
  </svg>
  </div>
  <p class="empty-title">还没有添加邮箱账号</p>
  <p class="empty-desc">点击上方「添加账号」按钮，添加你的邮箱即可开始使用</p>
  </div>

  <!-- 账号列表 -->
  <div v-else class="account-sections">
  <div v-for="section in groupedAccounts" :key="section.key" class="account-section">
  <!-- 分组标题 -->
  <div class="section-header">
  <span class="section-icon" v-html="section.icon"></span>
  <h3 class="section-title">{{ section.title }}</h3>
  <span class="section-count">{{ section.accounts.length }}</span>
  </div>
  <!-- 账号卡片 -->
  <div class="account-list">
  <div v-for="account in section.accounts" :key="account.id" class="account-card" @click="openEditDialog(account)">
  <!-- 平台图标头像 -->
  <div class="account-avatar" :class="account.provider" v-html="providerIcon(account.provider)"></div>
  <!-- 账号信息 -->
  <div class="account-info">
  <div class="info-main">
  <span class="account-name">
  <span v-if="account.remark" class="name-remark">{{ account.remark }}</span>
  <span v-if="!account.remark" class="name-email">{{ account.email }}</span>
  </span>
  <span v-if="account.remark && !account.hide_email" class="account-email-sub">{{ account.email }}</span>
  </div>
  <div class="info-meta">
  <span class="meta-provider">{{ providerName(account.provider) }}</span>
  <span class="meta-sep">·</span>
  <div class="account-status" :class="account.status">
  <span class="status-dot"></span>
  {{ statusText(account.status) }}
  </div>
  </div>
  </div>
  <!-- 操作按钮 -->
  <div class="card-actions">
  <button v-if="mailStore.reauthAccountIds.has(account.id)" class="btn-reauth-card" @click.stop="reauthorizeAccount(account)" title="重新授权">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 4v6h-6"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
  重新授权
  </button>
  <button class="edit-btn" @click.stop="openEditDialog(account)" title="编辑">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
  </svg>
  </button>
  </div>
  </div>
  </div>
  </div>
  </div>

  <!-- 添加账号对话框 -->
  <div v-if="showAddDialog" class="dialog-overlay" @click.self="showAddDialog = false">
  <div class="dialog">
  <h3 class="dialog-title">添加邮箱账号</h3>
  <p class="dialog-desc">选择邮箱服务商，授权后即可使用</p>
  <div class="provider-grid">
  <button v-for="p in providers" :key="p.type" class="provider-card" :class="{ active: selectedProvider === p.type }" @click="selectedProvider = p.type">
  <div class="provider-icon" v-html="p.icon"></div>
  <span class="provider-name">{{ p.name }}</span>
  </button>
  </div>
  <div class="dialog-actions">
  <button class="btn btn-secondary" @click="showAddDialog = false">取消</button>
  <button class="btn btn-primary" @click="startAuth" :disabled="!selectedProvider">
  {{ (selectedProvider === 'qq' || selectedProvider === 'netease' || selectedProvider === 'sina' || selectedProvider === 'custom') ? '下一步' : '授权登录' }}
  </button>
  </div>
  </div>
  </div>

  <!-- 腾讯邮箱授权码对话框 -->
  <div v-if="showQQDialog" class="dialog-overlay" @click.self="showQQDialog = false">
  <div class="dialog" style="width: 360px;">
  <h3 class="dialog-title">{{ qqForm.is_exmail ? '添加腾讯企业邮箱' : '添加腾讯邮箱' }}</h3>
  <div style="display: flex; align-items: center; gap: 8px; margin-bottom: var(--space-5);">
  <button class="toggle-switch" :class="{ active: qqForm.is_exmail }" @click="qqForm.is_exmail = !qqForm.is_exmail" type="button">
  <span class="toggle-knob"></span>
  </button>
  <span style="font-size: var(--text-sm); color: var(--text-secondary);">腾讯企业邮箱</span>
  </div>
  <div class="qq-form">
  <div class="form-field">
  <label class="field-label">邮箱地址</label>
  <input v-model="qqForm.email" class="input" type="email" :placeholder="qqForm.is_exmail ? 'yourname@yourcompany.com' : 'example@qq.com'" />
  </div>
  <div class="form-field">
  <label class="field-label">{{ qqForm.is_exmail ? '客户端专用密码' : '授权码' }}</label>
  <input v-model="qqForm.auth_code" class="input" type="password" :placeholder="qqForm.is_exmail ? '腾讯企业邮箱客户端专用密码' : 'QQ邮箱授权码'" />
  <p class="field-hint" v-if="!qqForm.is_exmail">
  授权码需要在QQ邮箱设置中开启IMAP/SMTP服务后获取
  <a href="https://service.mail.qq.com/detail?search=SMTP/IMAP" target="_blank" class="hint-link">查看教程</a>
  </p>
  <p class="field-hint" v-else>
  需管理员开启IMAP/SMTP服务，用户开启安全登录后生成客户端专用密码
  <a href="https://open.work.weixin.qq.com/help/wap/detail?docid=19886" target="_blank" class="hint-link">查看教程</a>
  </p>
  </div>
  </div>
  <div class="dialog-actions">
  <button class="btn btn-secondary" @click="showQQDialog = false">取消</button>
  <button class="btn btn-primary" @click="addQQAccount" :disabled="!qqForm.email || !qqForm.auth_code">添加账号</button>
  </div>
  </div>
  </div>

  <!-- 网易邮箱授权码对话框 -->
  <div v-if="showNeteaseDialog" class="dialog-overlay" @click.self="showNeteaseDialog = false">
  <div class="dialog">
  <h3 class="dialog-title">添加网易邮箱</h3>
  <p class="dialog-desc">请输入网易邮箱地址（163/126/188/yeah.net）和授权码</p>
  <div class="qq-form">
  <div class="form-field">
  <label class="field-label">邮箱地址</label>
  <input v-model="neteaseForm.email" class="input" type="email" placeholder="example@163.com / @126.com / @188.com" />
  </div>
  <div class="form-field">
  <label class="field-label">授权码</label>
  <input v-model="neteaseForm.auth_code" class="input" type="password" placeholder="网易邮箱授权码" />
  <p class="field-hint">
  授权码需要在网易邮箱设置中开启IMAP/SMTP服务后获取
  <a href="https://help.mail.163.com/searchFAQ.do?m=search&word=POP3/SMTP/IMAP" target="_blank" class="hint-link">查看教程</a>
  </p>
  </div>
  </div>
  <div class="dialog-actions">
  <button class="btn btn-secondary" @click="showNeteaseDialog = false">取消</button>
  <button class="btn btn-primary" @click="addNeteaseAccount" :disabled="!neteaseForm.email || !neteaseForm.auth_code">添加账号</button>
  </div>
  </div>
  </div>

  <!-- 新浪邮箱授权码对话框 -->
  <div v-if="showSinaDialog" class="dialog-overlay" @click.self="showSinaDialog = false">
  <div class="dialog">
  <h3 class="dialog-title">添加新浪邮箱</h3>
  <p class="dialog-desc">请输入新浪邮箱地址和授权码</p>
  <div class="qq-form">
  <div class="form-field">
  <label class="field-label">邮箱地址</label>
  <input v-model="sinaForm.email" class="input" type="email" placeholder="example@sina.com / @sina.cn / @vip.sina.com" />
  </div>
  <div class="form-field">
  <label class="field-label">授权码</label>
  <input v-model="sinaForm.auth_code" class="input" type="password" placeholder="新浪邮箱授权码" />
  <p class="field-hint">
  授权码需要在新浪邮箱设置中开启IMAP/SMTP服务后获取
  <a href="https://mail.sina.com.cn/help2.html" target="_blank" class="hint-link">查看教程</a>
  </p>
  </div>
  </div>
  <div class="dialog-actions">
  <button class="btn btn-secondary" @click="showSinaDialog = false">取消</button>
  <button class="btn btn-primary" @click="addSinaAccount" :disabled="!sinaForm.email || !sinaForm.auth_code">添加账号</button>
  </div>
  </div>
  </div>

  <!-- iCloud邮箱应用专用密码对话框 -->
  <div v-if="showICloudDialog" class="dialog-overlay" @click.self="showICloudDialog = false">
  <div class="dialog">
  <h3 class="dialog-title">添加iCloud邮箱</h3>
  <p class="dialog-desc">请输入iCloud邮箱地址和应用专用密码</p>
  <div class="qq-form">
  <div class="form-field">
  <label class="field-label">iCloud邮箱地址</label>
  <input v-model="icloudForm.email" class="input" type="email" placeholder="example@icloud.com" />
  </div>
  <div class="form-field">
  <label class="field-label">应用专用密码</label>
  <input v-model="icloudForm.auth_code" class="input" type="password" placeholder="Apple ID 应用专用密码" />
  <p class="field-hint">
  应用专用密码需要在 Apple ID 账户页面生成
  <a href="https://appleid.apple.com/account/manage" target="_blank" class="hint-link">前往生成</a>
  </p>
  </div>
  </div>
  <div class="dialog-actions">
  <button class="btn btn-secondary" @click="showICloudDialog = false">取消</button>
  <button class="btn btn-primary" @click="addICloudAccount" :disabled="!icloudForm.email || !icloudForm.auth_code">添加账号</button>
  </div>
  </div>
  </div>

  <!-- 自定义邮箱（标准 IMAP/SMTP）对话框 -->
  <div v-if="showCustomDialog" class="dialog-overlay" @click.self="showCustomDialog = false">
  <div class="dialog" style="width: 420px;">
  <h3 class="dialog-title">添加自定义邮箱</h3>
  <p class="dialog-desc">支持所有标准 IMAP/SMTP 协议的邮箱服务</p>
  <div class="qq-form">
  <!-- 邮箱地址 -->
  <div class="form-field">
  <label class="field-label">邮箱地址</label>
  <input v-model="customForm.email" class="input" type="email" placeholder="example@example.com" />
  </div>
  <!-- 授权码/密码 -->
  <div class="form-field">
  <label class="field-label">授权码 / 密码</label>
  <input v-model="customForm.auth_code" class="input" type="password" placeholder="邮箱授权码或登录密码" />
  <p class="field-hint">部分邮箱需要在设置中开启 IMAP/SMTP 服务并生成授权码</p>
  </div>
  <!-- IMAP 服务器配置 -->
  <div class="form-field">
  <label class="field-label">IMAP 服务器</label>
  <div class="form-row">
  <input v-model="customForm.imap_host" class="input" type="text" placeholder="imap.example.com" />
  <input v-model.number="customForm.imap_port" class="input port-input" type="number" placeholder="993" />
  </div>
  <p class="field-hint">用于收信。139 邮箱这类服务通常使用 143 + 不加密</p>
  </div>
  <!-- IMAP 加密方式 -->
  <div class="form-field">
  <label class="field-label">IMAP 加密方式</label>
  <select class="input ssl-select" :value="customForm.imap_ssl" @change="onImapSslChange(($event.target as HTMLSelectElement).value as 'ssl' | 'starttls' | 'none')">
  <option value="ssl">SSL 直连（默认 993）</option>
  <option value="starttls">STARTTLS（默认 143）</option>
  <option value="none">不加密（默认 143）</option>
  </select>
  <p class="field-hint">切换加密方式时端口会自动联动，可手动修改</p>
  </div>
  <!-- SMTP 服务器配置 -->
  <div class="form-field">
  <label class="field-label">SMTP 服务器</label>
  <div class="form-row">
  <input v-model="customForm.smtp_host" class="input" type="text" placeholder="smtp.example.com" />
  <input v-model.number="customForm.smtp_port" class="input port-input" type="number" placeholder="465" />
  </div>
  </div>
  <!-- SMTP 加密方式 -->
  <div class="form-field">
  <label class="field-label">SMTP 加密方式</label>
  <select class="input ssl-select" :value="customForm.smtp_ssl" @change="onSmtpSslChange(($event.target as HTMLSelectElement).value as 'ssl' | 'starttls')">
  <option value="ssl">SSL 直连（默认 465）</option>
  <option value="starttls">STARTTLS（默认 587）</option>
  </select>
  <p class="field-hint">切换加密方式时端口会自动联动，可手动修改</p>
  </div>
  </div>
  <div class="dialog-actions">
  <button class="btn btn-secondary" @click="showCustomDialog = false">取消</button>
  <button class="btn btn-primary" @click="addCustomAccount" :disabled="!customForm.email || !customForm.auth_code || !customForm.imap_host || !customForm.smtp_host">添加账号</button>
  </div>
  </div>
  </div>

  <!-- 编辑账号对话框 -->
  <div v-if="showEditDialog" class="dialog-overlay" @click.self="showEditDialog = false">
  <div class="dialog">
  <h3 class="dialog-title">编辑账号</h3>
  <p class="dialog-desc">{{ editingAccount?.email }}</p>
  <div class="edit-form">
  <div class="form-field">
  <label class="field-label">备注名</label>
  <input v-model="editForm.remark" class="input" type="text" placeholder="如：工作邮箱" />
  </div>
  <div class="form-field">
  <label class="field-label">分组</label>
  <input v-model="editForm.group_name" class="input" type="text" placeholder="如：工作、个人" />
  <div v-if="existingGroups.length" class="group-tags">
  <button v-for="g in existingGroups" :key="g" class="group-tag" :class="{ active: editForm.group_name === g }" @click="editForm.group_name = g">{{ g }}</button>
  </div>
  </div>
  <div class="form-field toggle-field">
  <span class="toggle-label">隐藏邮箱地址</span>
  <button class="toggle-switch" :class="{ active: editForm.hide_email }" @click="editForm.hide_email = !editForm.hide_email" type="button">
  <span class="toggle-knob"></span>
  </button>
  </div>
  </div>
  <div class="dialog-actions">
  <button class="btn btn-secondary" @click="showEditDialog = false">取消</button>
  <button class="btn btn-danger-text" @click="confirmDelete(editingAccount!)">删除账号</button>
  <button class="btn btn-primary" @click="saveEdit">保存</button>
  </div>
  </div>
  </div>
  </div>
</template>

<script setup lang="ts">
import { openAuthWindowSync, navigateAuthWindow, closeAuthWindow, authWindowBlockedMessage } from '../utils/oauthWindow';
import { ref, computed, onMounted } from 'vue';
import api from '../utils/api';
import { useUIStore } from '../stores/ui';
import { useMailStore } from '../stores/mail';
import { providerIcon, providerName } from '../utils/provider';
import { useWebSocket } from '../composables/useWebSocket';

const ui = useUIStore();
const mailStore = useMailStore();

// WebSocket 实时同步：监听账号连接状态变化，自动更新账号列表状态
function handleWsMessage(data: any) {
  if (data.type === 'connection_status') {
  const account = mailStore.accounts.find(a => a.id === data.account_id);
  if (account) {
  if (data.status === 'reauth_needed') {
  account.status = 'reauth_needed';
  mailStore.reauthAccountIds.add(data.account_id);
  } else {
  account.status = data.status === 'connected' ? 'connected' : 'error';
  if (data.status === 'connected') {
  mailStore.reauthAccountIds.delete(data.account_id);
  }
  }
  }
  }
}
const { connect: connectWs } = useWebSocket(handleWsMessage);

// 使用 store 中的账号列表，不再维护本地副本
const loading = ref(true);
const sortBy = ref<'group' | 'platform'>('platform');
const showAddDialog = ref(false);
const showQQDialog = ref(false);
const showNeteaseDialog = ref(false);
const showSinaDialog = ref(false);
const showICloudDialog = ref(false);
const showCustomDialog = ref(false);
const showEditDialog = ref(false);
const selectedProvider = ref('gmail');
const qqForm = ref({ email: '', auth_code: '', is_exmail: false });
const neteaseForm = ref({ email: '', auth_code: '' });
const sinaForm = ref({ email: '', auth_code: '' });
const icloudForm = ref({ email: '', auth_code: '' });
// 自定义邮箱表单：邮箱地址 + 授权码 + IMAP/SMTP 服务器配置
const customForm = ref({
  email: '',
  auth_code: '',
  imap_host: '',
  imap_port: 993,
  imap_ssl: 'ssl' as 'ssl' | 'starttls' | 'none',
  smtp_host: '',
  smtp_port: 465,
  smtp_ssl: 'ssl' as 'ssl' | 'starttls',
});
const MICROSOFT_ICON_SVG = '<svg width="24" height="24" viewBox="0 0 1024 1024"><path d="M0.10238 51.189762h460.503099v460.503099H0.10238V51.189762z" fill="#F45325"/><path d="M512.204759 51.189762H972.707858v460.503099h-460.503099V51.189762z" fill="#81BD06"/><path d="M0.10238 563.292142h460.503099v460.656668H0.10238v-460.656668z" fill="#04A6EF"/><path d="M512.204759 563.292142H972.707858v460.656668h-460.503099v-460.656668z" fill="#FFBA07"/></svg>';
const editingAccount = ref<any>(null);
const editForm = ref({ remark: '', group_name: '', hide_email: false });

const providers = [
  {
  type: 'gmail',
  name: 'Gmail',
  icon: '<svg width="24" height="24" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>',
  },
  {
  type: 'qq',
  name: '腾讯邮箱',
  icon: '<svg width="24" height="24" viewBox="0 0 1024 1024"><path d="M211.101867 363.776c-14.933333 66.56-7.466667 133.12 7.466666 192.256 14.933333 51.754667-7.466667 103.509333-52.309333 133.077333-67.285333 36.949333-149.461333-14.805333-156.970667-81.322666C-57.954133 260.266667 255.944533-57.642667 614.728533 8.874667c-209.28 22.186667-366.250667 162.688-403.626666 354.901333z" fill="#FFDC04"/><path d="M532.4672 844.373333c59.818667-22.186667 119.594667-59.136 164.437333-103.509333 37.376-36.992 97.152-44.373333 141.994667-14.805333 67.285333 36.992 67.285333 133.12 7.509333 177.493333-269.098667 229.162667-702.549333 118.272-822.186666-221.866667 112.128 162.688 321.408 221.866667 508.245333 162.688z" fill="#E03A22"/><path d="M794.056533 326.826667a425.173333 425.173333 0 0 0-171.861333-88.746667c-52.352-14.762667-89.728-59.136-89.728-110.933333 0-73.898667 82.218667-125.653333 149.504-96.085334 336.341333 118.314667 455.893333 539.733333 216.746667 813.312 89.685333-177.493333 37.376-391.850667-104.661334-517.546666z" fill="#27AA3A"/><path d="M652.104533 489.472c0-14.805333 0-29.568-7.509333-36.949333 0-7.424 0-7.424-7.466667-14.805334 0-73.941333-44.842667-133.12-127.061333-133.12-82.218667 0-127.061333 59.178667-127.061333 133.12 0 7.381333-7.466667 7.381333-7.466667 14.805334-7.466667 14.762667-7.466667 22.186667-7.466667 29.568v7.381333c-14.933333 7.381333-29.909333 29.568-37.376 51.754667-14.933333 36.949333-14.933333 73.941333-7.466666 73.941333 7.466667 7.381333 22.4-7.381333 37.333333-22.186667 0 22.186667 14.933333 44.373333 29.909333 59.136-14.933333 0-29.866667 14.805333-29.866666 29.568 0 22.186667 29.866667 36.992 74.709333 36.992 37.376 0 67.285333-14.805333 74.752-29.568h7.466667c7.466667 14.762667 37.376 29.568 74.752 29.568s74.752-14.805333 74.752-36.992c0-14.762667-14.933333-22.186667-29.909334-29.568 14.933333-14.762667 29.866667-29.568 37.376-51.754666 14.933333 22.186667 29.866667 29.568 37.376 22.186666 14.933333-7.381333 7.466667-36.949333-7.466667-73.941333-7.466667-22.186667-22.4-44.373333-37.376-51.754667v-7.381333z" fill="#2B2B2B"/></svg>',
  },
  {
  type: 'netease',
  name: '网易邮箱',
  icon: '<svg width="24" height="24" viewBox="0 0 1024 1024"><path d="M592.298667 661.76c60.458667-47.573333 67.072-49.92 84.992-27.392 15.573333 19.242667 12.245333 22.741333-91.733334 113.365333-34.688 30.592-63.744 62.293333-63.744 71.381334 0 7.936-8.96 14.762667-19.029333 14.762666-10.026667 0-46.933333 19.285333-81.493333 44.288C353.024 926.890667 227.84 981.333333 184.192 981.333333c-71.466667 0-67.072-71.381333 5.632-91.733333 124.117333-34.090667 251.605333-106.581333 402.432-227.84z m-46.848-200.618667c14.506667-5.717333 39.125333-7.978667 54.826666-5.589333 15.573333 1.109333 51.370667 5.674667 80.426667 9.045333 128.512 14.805333 224.64 132.693333 214.613333 259.626667-5.546667 70.229333-24.576 106.538667-81.578666 158.634667-89.514667 81.536-214.698667 121.216-257.109334 82.688-27.989333-26.112-50.304-81.706667-41.344-103.210667 5.546667-15.914667 10.069333-15.914667 41.344 1.152 70.4 36.266667 171.008-2.261333 229.12-87.296 58.154667-86.186667 33.493333-180.266667-46.933333-180.266667-29.056 0-40.234667-6.741333-51.370667-31.701333-21.333333-44.16-63.744-46.378667-111.829333-4.48-223.530667 196.053333-431.488 302.592-478.421333 245.930667-30.165333-36.224-6.741333-54.357333 117.333333-90.666667 42.538667-12.544 112.938667-49.834667 191.146667-103.168 111.786667-74.752 124.074667-86.058667 119.68-112.170667-4.522667-21.504 0-30.592 20.096-38.528z m-191.146667-410.282666c60.330667-12.458667 257.024-10.24 307.370667 3.328 95.061333 25.002667 110.634667 41.941333 138.666666 160 16.725333 70.272 15.616 101.973333-4.522666 150.698666-22.314667 55.594667-64.853333 69.12-201.216 68.010667-109.610667-1.109333-111.786667 0-130.816 29.44-23.509333 38.442667-118.570667 114.432-160.981334 130.346667-128.512 46.378667-200.106667 50.944-211.285333 14.677333-11.136-35.2 13.397333-56.704 66.005333-56.704 65.834667 0 174.336-44.245333 205.610667-82.773333 12.245333-13.568 4.437333-17.066667-48.085333-21.546667-70.4-5.589333-95.018667-28.330667-108.373334-99.712-12.245333-66.56 7.466667-125.738667 52.309334-147.242667 22.314667-10.24 74.922667-22.186667 119.765333-29.568 44.842667-5.674667 89.685333-22.186667 97.152-36.949333 7.466667-14.805333 29.866667-22.186667 52.309333-14.805333 22.314667 7.381333 52.309333 2.261333 67.242667-10.24 22.314667-19.242667 37.376-17.066667 52.309333 5.674666 14.933333 22.186667 44.842667 29.568 82.218667 22.186667z" fill="#C5161C"/></svg>',
  },
  {
  type: 'sina',
  name: '新浪邮箱',
  icon: '<svg width="24" height="24" viewBox="0 0 1024 1024"><path d="M769.92256 503.466667c-40.96-8.618667-21.162667-30.250667-21.162667-30.250667s39.509333-66.218667-8.490666-115.2c-59.306667-60.458667-201.856 7.253333-201.856 7.253333-55.04 17.237333-39.552-7.253333-32.469334-50.432 0-50.389333-16.938667-135.381333-162.346666-84.949333-142.592 51.84-266.837333 228.949333-266.837334 228.949333C-10.792107 576.853333 0.471893 667.648 0.471893 667.648c21.162667 201.6 231.552 256.298667 393.898667 269.269333 172.202667 14.421333 402.346667-60.458667 472.917333-213.12 72.021333-151.210667-56.448-211.669333-97.408-220.330666m-361.386666 377.301333c-170.837333 7.210667-307.797333-79.232-307.797334-195.84 0-116.650667 136.96-208.810667 307.797334-217.472 169.386667-7.168 307.754667 64.853333 307.754666 180.053333 0 116.608-138.368 224.597333-307.754666 233.258667" fill="#D81E06"/><path d="M374.65856 545.237333c-170.837333 20.138667-151.04 184.32-151.04 184.32s-1.450667 51.84 46.549333 77.738667c100.266667 54.741333 203.306667 21.632 255.530667-47.488 50.816-67.712 19.754667-234.752-151.04-214.613333m-43.776 228.992c-32.469333 4.309333-57.898667-14.378667-57.898667-41.770667 0-27.306667 22.613333-56.149333 55.04-59.008 36.693333-2.901333 60.714667 18.688 60.714667 44.629333 0 27.349333-25.386667 53.290667-57.856 56.149334m100.224-87.850667c-11.306667 8.661333-23.978667 7.253333-29.653333-2.858667a25.770667 25.770667 0 0 1 7.082666-33.109333c12.672-10.112 25.386667-7.253333 31.061334 2.858667 7.04 10.069333 2.816 24.490667-8.490667 33.109333" fill="#2C2C2C"/><path d="M1018.413227 412.757333c1.408-2.901333 1.408-7.210667 1.408-10.069333 2.816-15.872 4.224-31.701333 4.224-47.530667C1024.045227 182.357333 885.677227 42.666667 716.29056 42.666667c-24.021333 0-42.368 18.730667-42.368 43.221333 0 24.448 18.346667 43.178667 42.368 43.178667 122.794667 0 221.653333 100.821333 221.653333 226.090666 0 14.378667-1.408 27.349333-4.266666 41.770667v4.266667c0 24.533333 18.346667 43.221333 42.368 43.221333 21.162667 0 38.101333-12.928 42.368-31.658667" fill="#D81E06"/><path d="M885.677227 370.986667c0-5.76 1.408-10.069333 1.408-15.829334 0-95.061333-76.202667-172.8-169.386667-172.8a35.285333 35.285333 0 0 0-35.285333 36.010667c0 20.138667 15.530667 35.968 35.285333 35.968 55.04 0 98.816 44.672 98.816 100.821333 0 4.309333 0 8.618667-1.408 12.970667h1.408c0 1.408-1.408 2.858667-1.408 4.266667 0 20.181333 15.530667 36.053333 35.285333 36.053333 18.346667 0 32.469333-14.421333 33.877334-31.701333v-2.858667c1.408 0 1.408 0 1.408-2.901333 0 1.450667 0 1.450667 0 0" fill="#D81E06"/></svg>',
  },
  {
  type: 'icloud',
  name: 'iCloud邮箱',
  icon: '<svg width="24" height="24" viewBox="0 0 1024 1024"><path d="M791.488 544.095c-1.28-129.695 105.76-191.871 110.528-194.975-60.16-88.032-153.856-100.064-187.232-101.472-79.744-8.064-155.584 46.944-196.064 46.944-40.352 0-102.816-45.76-168.96-44.544-86.912 1.28-167.072 50.528-211.808 128.384-90.304 156.703-23.136 388.831 64.896 515.935 43.008 62.208 94.304 132.064 161.632 129.568 64.832-2.592 89.376-41.952 167.744-41.952s100.416 41.952 169.056 40.672c69.76-1.312 113.984-63.392 156.704-125.792 49.376-72.16 69.728-142.048 70.912-145.632-1.536-0.704-136.064-52.224-137.408-207.136zM662.56 163.52C698.304 120.16 722.432 60 715.84 0c-51.488 2.112-113.888 34.304-150.816 77.536-33.152 38.368-62.144 99.616-54.368 158.432 57.472 4.48 116.128-29.216 151.904-72.448z" fill="currentColor"/></svg>',
  },
  {
  type: 'outlook',
  name: 'Microsoft',
  icon: MICROSOFT_ICON_SVG,
  },
  {
  // 自定义邮箱：用户填写 IMAP/SMTP 配置，兼容所有标准协议邮箱
  type: 'custom',
  name: '自定义邮箱',
  icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 7l-10 5L2 7"/></svg>',
  },
];
const existingGroups = computed(() => {
  const groups = new Set<string>();
  mailStore.accounts.forEach(a => { if (a.group_name) groups.add(a.group_name); });
  return [...groups];
});

// 按分组或平台组织账号
const groupedAccounts = computed(() => {
  if (sortBy.value === 'platform') {
  const map = new Map<string, any[]>();
  mailStore.accounts.forEach(a => {
  const key = a.provider;
  if (!map.has(key)) map.set(key, []);
  map.get(key)!.push(a);
  });
  return [...map.entries()].map(([key, accs]) => ({
  key,
  title: providerName(key),
  icon: providerIcon(key),
  accounts: accs,
  }));
  } else {
  const map = new Map<string, any[]>();
  mailStore.accounts.forEach(a => {
  const key = a.group_name || '未分组';
  if (!map.has(key)) map.set(key, []);
  map.get(key)!.push(a);
  });
  return [...map.entries()].map(([key, accs]) => ({
  key,
  title: key,
  icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>',
  accounts: accs,
  }));
  }
});

onMounted(async () => {
  connectWs();
  await mailStore.loadAccounts();
  loading.value = false;
  // 立即将所有账号状态设为 checking，避免 sessionStorage 缓存的旧状态闪烁
  mailStore.accounts.forEach((account: any) => { account.status = 'checking'; });
  const oauthJustAdded = sessionStorage.getItem('flymail_oauth_just_added') === '1';
  if (oauthJustAdded) {
  // OAuth 成功后后端还在启动同步/刷新令牌，立即测试容易把临时 token 状态误报成 invalid token。
  sessionStorage.removeItem('flymail_oauth_just_added');
  mailStore.accounts.forEach((account: any) => { account.status = 'connected'; });
  return;
  }
  checkAllAccountsStatus();
});

async function checkAllAccountsStatus() {
  for (const account of mailStore.accounts) {
  // 已知需要重新授权的账号跳过测试
  if (mailStore.reauthAccountIds.has(account.id)) {
  account.status = 'reauth_needed';
  continue;
  }
  account.status = 'checking';
  }
  await Promise.allSettled(
  mailStore.accounts.map(async (account) => {
  if (account.status === 'reauth_needed') return;
  try {
  const data = await api.post(`/accounts/${account.id}/test`) as any;
  account.status = data.success ? 'connected' : 'error';
  if (!data.success) {
  console.warn('账号连接检测失败:', account.email, data.error || '未知错误');
  }
  } catch {
  account.status = 'error';
  }
  })
  );
}

/** 启动邮箱认证流程：Gmail/Outlook 使用 OAuth 弹窗授权，QQ/网易/iCloud 使用授权码对话框 */
async function startAuth() {
  if (selectedProvider.value === 'qq') {
  showAddDialog.value = false;
  showQQDialog.value = true;
  return;
  }
  if (selectedProvider.value === 'netease') {
  showAddDialog.value = false;
  showNeteaseDialog.value = true;
  return;
  }
  if (selectedProvider.value === 'sina') {
  showAddDialog.value = false;
  showSinaDialog.value = true;
  return;
  }
  if (selectedProvider.value === 'icloud') {
  showAddDialog.value = false;
  showICloudDialog.value = true;
  return;
  }
  if (selectedProvider.value === 'custom') {
  showAddDialog.value = false;
  showCustomDialog.value = true;
  return;
  }
  // 必须在 await 前同步打开窗口，否则飞牛 App WebView 会静默拦截（尤其 Google）
  const providerLabel = selectedProvider.value === 'outlook' ? 'Microsoft' : 'Google';
  const { win: authWindow } = openAuthWindowSync(providerLabel);
  if (!authWindow) {
    ui.error(authWindowBlockedMessage(providerLabel));
    return;
  }
  try {
    // Gmail / Microsoft 都走 Cloudflare Broker，前端不再传本地 redirect_uri。
    const data = await api.post('/accounts/auth-url', {
      provider: selectedProvider.value,
    }) as any;
    if (data.error) {
      closeAuthWindow(authWindow);
      ui.error('获取授权链接失败：' + data.error);
      return;
    }
    if (data.auth_url) {
      if (!navigateAuthWindow(authWindow, data.auth_url)) {
        ui.error(authWindowBlockedMessage(providerLabel));
      }
    } else {
      closeAuthWindow(authWindow);
      ui.error('获取授权链接失败');
    }
  } catch (e: any) {
    closeAuthWindow(authWindow);
    ui.error('获取授权链接失败：' + (e.response?.data?.error || e.message || '网络错误'));
  }
}
async function addQQAccount() {
  if (!qqForm.value.email || !qqForm.value.auth_code) { ui.warning('请填写邮箱地址和授权码'); return; }
  try {
  const data = await api.post('/accounts/add-qq', { email: qqForm.value.email, auth_code: qqForm.value.auth_code, is_exmail: qqForm.value.is_exmail }, { timeout: 30000 }) as any;
  if (data.success) {
  ui.success(qqForm.value.is_exmail ? '腾讯企业邮箱添加成功！' : '腾讯邮箱添加成功！');
  showQQDialog.value = false;
  qqForm.value = { email: '', auth_code: '', is_exmail: false };
  await mailStore.loadAccounts();
  checkAllAccountsStatus();
  } else {
  ui.error('添加失败：' + (data.error || '未知错误'));
  }
  } catch (e: any) {
  ui.error('添加失败：' + (e.response?.data?.error || e.message || '网络错误'));
  }
}

async function addNeteaseAccount() {
  if (!neteaseForm.value.email || !neteaseForm.value.auth_code) { ui.warning('请填写邮箱地址和授权码'); return; }
  const email = neteaseForm.value.email.toLowerCase();
  const validSuffixes = ['@163.com', '@126.com', '@188.com', '@yeah.net'];
  if (!validSuffixes.some(s => email.endsWith(s))) {
  ui.warning('请输入163、126、188或yeah.net邮箱地址');
  return;
  }
  try {
  const data = await api.post('/accounts/add-netease', { email: neteaseForm.value.email, auth_code: neteaseForm.value.auth_code }, { timeout: 30000 }) as any;
  if (data.success) {
  ui.success('网易邮箱添加成功！');
  showNeteaseDialog.value = false;
  neteaseForm.value = { email: '', auth_code: '' };
  await mailStore.loadAccounts();
  checkAllAccountsStatus();
  } else {
  ui.error('添加失败：' + (data.error || '未知错误'));
  }
  } catch (e: any) {
  ui.error('添加失败：' + (e.response?.data?.error || e.message || '网络错误'));
  }
}

async function addSinaAccount() {
  if (!sinaForm.value.email || !sinaForm.value.auth_code) { ui.warning('请填写邮箱地址和授权码'); return; }
  const email = sinaForm.value.email.toLowerCase();
  const validSuffixes = ['@sina.com', '@sina.cn', '@2008.sina.com', '@vip.sina.com', '@vip.sina.cn'];
  if (!validSuffixes.some(s => email.endsWith(s))) {
  ui.warning('请输入sina.com、sina.cn、2008.sina.com、vip.sina.com或vip.sina.cn邮箱地址');
  return;
  }
  try {
  const data = await api.post('/accounts/add-sina', { email: sinaForm.value.email, auth_code: sinaForm.value.auth_code }, { timeout: 30000 }) as any;
  if (data.success) {
  ui.success('新浪邮箱添加成功！');
  showSinaDialog.value = false;
  sinaForm.value = { email: '', auth_code: '' };
  await mailStore.loadAccounts();
  checkAllAccountsStatus();
  } else {
  ui.error('添加失败：' + (data.error || '未知错误'));
  }
  } catch (e: any) {
  ui.error('添加失败：' + (e.response?.data?.error || e.message || '网络错误'));
  }
}

async function addICloudAccount() {
  if (!icloudForm.value.email || !icloudForm.value.auth_code) { ui.warning('请填写邮箱地址和应用专用密码'); return; }
  const email = icloudForm.value.email.toLowerCase();
  const validSuffixes = ['@icloud.com', '@me.com', '@mac.com'];
  if (!validSuffixes.some(s => email.endsWith(s))) {
  ui.warning('请输入icloud.com、me.com或mac.com邮箱地址');
  return;
  }
  try {
  const data = await api.post('/accounts/add-icloud', { email: icloudForm.value.email, auth_code: icloudForm.value.auth_code }, { timeout: 30000 }) as any;
  if (data.success) {
  ui.success('iCloud邮箱添加成功！');
  showICloudDialog.value = false;
  icloudForm.value = { email: '', auth_code: '' };
  await mailStore.loadAccounts();
  checkAllAccountsStatus();
  } else {
  ui.error('添加失败：' + (data.error || '未知错误'));
  }
  } catch (e: any) {
  ui.error('添加失败：' + (e.response?.data?.error || e.message || '网络错误'));
  }
}

/** IMAP 加密方式切换：联动默认端口（SSL→993，STARTTLS/不加密→143） */
function onImapSslChange(value: 'ssl' | 'starttls' | 'none') {
  customForm.value.imap_ssl = value;
  customForm.value.imap_port = value === 'ssl' ? 993 : 143;
}

/** SMTP 加密方式切换：联动默认端口（SSL→465，STARTTLS→587） */
function onSmtpSslChange(value: 'ssl' | 'starttls') {
  customForm.value.smtp_ssl = value;
  customForm.value.smtp_port = value === 'ssl' ? 465 : 587;
}

/** 添加自定义邮箱账号（标准 IMAP/SMTP 协议） */
async function addCustomAccount() {
  if (!customForm.value.email || !customForm.value.auth_code
  || !customForm.value.imap_host || !customForm.value.smtp_host) {
  ui.warning('请填写邮箱地址、授权码和 IMAP/SMTP 服务器地址');
  return;
  }
  try {
  const data = await api.post('/accounts/add-custom', {
  email: customForm.value.email,
  auth_code: customForm.value.auth_code,
  imap_host: customForm.value.imap_host,
  imap_port: customForm.value.imap_port,
  imap_ssl: customForm.value.imap_ssl,
  smtp_host: customForm.value.smtp_host,
  smtp_port: customForm.value.smtp_port,
  smtp_ssl: customForm.value.smtp_ssl,
  }, { timeout: 30000 }) as any;
  if (data.success) {
  ui.success('自定义邮箱添加成功！');
  showCustomDialog.value = false;
  customForm.value = { email: '', auth_code: '', imap_host: '', imap_port: 993, imap_ssl: 'ssl', smtp_host: '', smtp_port: 465, smtp_ssl: 'ssl' };
  await mailStore.loadAccounts();
  checkAllAccountsStatus();
  } else {
  ui.error('添加失败：' + (data.error || '未知错误'));
  }
  } catch (e: any) {
  ui.error('添加失败：' + (e.response?.data?.error || e.message || '网络错误'));
  }
}

function openEditDialog(account: any) {
  editingAccount.value = account;
  editForm.value = { remark: account.remark, group_name: account.group_name, hide_email: account.hide_email };
  showEditDialog.value = true;
}

async function saveEdit() {
  if (!editingAccount.value) return;
  try {
  await api.put(`/accounts/${editingAccount.value.id}`, editForm.value);
  editingAccount.value.remark = editForm.value.remark;
  editingAccount.value.group_name = editForm.value.group_name;
  editingAccount.value.hide_email = editForm.value.hide_email;
  showEditDialog.value = false;
  ui.success('保存成功');
  } catch {
  ui.error('保存失败');
  }
}

async function confirmDelete(account: any) {
  const ok = await ui.showConfirm({
  title: '删除账号',
  message: `确定要删除账号 ${account.email} 吗？此操作不可撤销。`,
  confirmText: '删除',
  danger: true,
  });
  if (ok) {
  try {
  await api.delete(`/accounts/${account.id}`);
  // mailStore.loadAccounts() 会从后端重新加载，无需手动过滤
  mailStore.clearCurrentAccountState();
  await mailStore.loadAccounts();
  await mailStore.loadFolders();
  showEditDialog.value = false;
  ui.success('账号已删除');
  } catch {
  ui.error('删除失败');
  }
  }
}


function statusText(status: string) {
  const map: Record<string, string> = {
  connected: '已连接',
  disconnected: '未连接',
  error: '连接异常',
  checking: '检测中',
  reauth_needed: '需要重新授权',
  };
  return map[status] || status;
}

/** 重新授权指定账号（与添加账号相同：先同步开窗，再跳转授权 URL） */
async function reauthorizeAccount(account: any) {
  const providerLabel = account.provider === 'outlook' ? 'Microsoft' : 'Google';
  // 必须在 await 前同步 open，否则飞牛手机 App 内点击「重新授权」会无反应
  const { win: authWindow } = openAuthWindowSync(providerLabel);
  if (!authWindow) {
    ui.error(authWindowBlockedMessage(providerLabel));
    return;
  }
  try {
    const data = await api.post('/accounts/auth-url', {
      provider: account.provider,
      user_uid: mailStore.user?.uid || '',
    }) as any;
    if (data.error) {
      closeAuthWindow(authWindow);
      ui.error('获取授权链接失败：' + data.error);
      return;
    }
    if (data.auth_url) {
      if (!navigateAuthWindow(authWindow, data.auth_url)) {
        ui.error(authWindowBlockedMessage(providerLabel));
      }
    } else {
      closeAuthWindow(authWindow);
      ui.error('获取授权链接失败');
    }
  } catch (e: any) {
    closeAuthWindow(authWindow);
    ui.error('获取授权链接失败：' + (e?.response?.data?.error || e?.message || '网络错误'));
  }
}

</script>

<style scoped>
.account-page {
  height: 100%;
  overflow-y: auto;
  padding: var(--space-6);
  background: var(--bg-secondary);
}

/* ==================== 工具栏 ==================== */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-5);
}

.sort-toggle {
  display: flex;
  background: var(--bg-tertiary);
  border-radius: var(--border-radius-full);
  padding: 3px;
  gap: 2px;
}

.toggle-btn {
  padding: 6px 18px;
  border: none;
  border-radius: var(--border-radius-full);
  background: transparent;
  color: var(--text-tertiary);
  font-size: var(--text-xs);
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.toggle-btn.active {
  background: var(--bg-primary);
  color: var(--text-primary);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

/* ==================== 加载状态 ==================== */
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-12);
  color: var(--text-tertiary);
  font-size: var(--text-sm);
}

.loading-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-accent);
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* ==================== 空状态 ==================== */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-12) var(--space-6);
  text-align: center;
}

.empty-icon {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: var(--bg-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  margin-bottom: var(--space-4);
}

.empty-title {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--space-1);
}

.empty-desc {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
}

/* ==================== 分组区域 ==================== */
.account-sections {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.section-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
  padding: 0 var(--space-1);
}

.section-icon {
  display: flex;
  align-items: center;
  color: var(--text-secondary);
}

.section-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-secondary);
}

.section-count {
  font-size: 11px;
  color: var(--text-tertiary);
  background: var(--bg-tertiary);
  padding: 1px 7px;
  border-radius: var(--border-radius-full);
  font-weight: 500;
}

/* ==================== 账号列表 ==================== */
.account-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/* 账号卡片 */
.account-card {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--bg-card);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-card);
  cursor: pointer;
  transition: all 0.2s ease;
}

.account-card:hover {
  box-shadow: var(--shadow-md);
  background: var(--bg-hover);
}

/* 平台图标头像 */
.account-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  line-height: 0;
}

.account-avatar.qq { background: #E8F4FD; }
.account-avatar.gmail { background: #FEE8E7; }
.account-avatar.netease { background: #FDE8E8; }
.account-avatar.sina { background: #FDE8E8; }

/* 账号信息 */
.account-info {
  flex: 1;
  min-width: 0;
}

.info-main {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  overflow: hidden;
}

.account-name {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.name-remark {
  color: var(--text-primary);
}

.name-email {
  color: var(--text-primary);
}

.account-email-sub {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex-shrink: 1;
  min-width: 0;
}

.info-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 2px;
}

.meta-provider {
  font-size: 11px;
  color: var(--text-tertiary);
}

.meta-sep {
  font-size: 11px;
  color: var(--border-color);
}

/* 编辑按钮 */
.edit-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: none;
  border-radius: var(--border-radius-sm);
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  flex-shrink: 0;
  transition: all var(--transition-fast);
  opacity: 0;
}

.account-card:hover .edit-btn {
  opacity: 1;
}

.edit-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

/* ==================== 状态标签 ==================== */
.account-status {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 500;
  padding: 1px 7px;
  border-radius: var(--border-radius-full);
}

.status-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
}

.account-status.connected { background: #E8F5E9; color: #2E7D32; }
.account-status.connected .status-dot { background: #4CAF50; }
.account-status.disconnected { background: var(--bg-tertiary); color: var(--text-tertiary); }
.account-status.disconnected .status-dot { background: var(--text-tertiary); }
.account-status.error { background: #FFEBEE; color: #C62828; }
.account-status.error .status-dot { background: #EF5350; }
.account-status.checking { background: #E3F2FD; color: #1565C0; }
.account-status.checking .status-dot { background: #42A5F5; animation: status-pulse 0.8s ease-in-out infinite; }
.account-status.reauth_needed { background: #FFF3E0; color: #E65100; }
.account-status.reauth_needed .status-dot { background: #FF9800; }

@keyframes status-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.7); }
}

/* 操作按钮区 */
.card-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

/* 重新授权按钮 */
.btn-reauth-card {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: #FFF3E0;
  border: 1px solid #FFB74D;
  border-radius: var(--border-radius-sm);
  color: #E65100;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.btn-reauth-card:hover {
  background: #FFE0B2;
}

:root.dark .btn-reauth-card {
  background: #3D2E00;
  border-color: #5A4400;
  color: #FFB74D;
}

:root.dark .btn-reauth-card:hover {
  background: #4A3800;
}

/* ==================== 对话框 ==================== */
.dialog-desc {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: var(--space-5);
  margin-top: calc(var(--space-1) * -1);
}

.provider-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}

.provider-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-4) var(--space-3);
  border: 2px solid var(--border-color);
  border-radius: var(--border-radius-md);
  background: var(--bg-primary);
  cursor: pointer;
  transition: all var(--transition-fast);
  font-family: inherit;
}

.provider-card:hover { border-color: var(--border-color-strong); background: var(--bg-hover); }
.provider-card.active { border-color: var(--color-accent); background: var(--color-accent-lighter); }

.provider-icon { display: flex; align-items: center; justify-content: center; }
.provider-name { font-size: var(--text-sm); font-weight: 500; color: var(--text-primary); }

/* 编辑表单 */
.edit-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.group-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin-top: var(--space-1);
}

.group-tag {
  padding: 3px 10px;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius-full);
  background: var(--bg-primary);
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-family: inherit;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.group-tag:hover { border-color: var(--color-accent); color: var(--color-accent); }
.group-tag.active { border-color: var(--color-accent); background: var(--color-accent-lighter); color: var(--color-accent); }

/* 隐藏邮箱 toggle */
.toggle-field {
  display: flex !important;
  flex-direction: row !important;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) 0;
}

.toggle-label {
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.toggle-switch {
  width: 36px;
  height: 20px;
  border-radius: 10px;
  border: none;
  background: var(--bg-tertiary);
  position: relative;
  cursor: pointer;
  transition: background var(--transition-fast);
  flex-shrink: 0;
}

.toggle-switch.active { background: var(--color-accent); }

.toggle-knob {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: white;
  transition: transform var(--transition-fast);
  box-shadow: 0 1px 2px rgba(0,0,0,0.15);
}

.toggle-switch.active .toggle-knob { transform: translateX(16px); }

/* QQ/网易表单 */
.qq-form { display: flex; flex-direction: column; gap: var(--space-4); }
.form-field { display: flex; flex-direction: column; gap: var(--space-2); }
.field-label { font-size: var(--text-sm); font-weight: 500; color: var(--text-primary); }
.field-hint { font-size: var(--text-xs); color: var(--text-tertiary); margin-top: var(--space-1); }
.hint-link { color: var(--color-accent); text-decoration: none; }
.hint-link:hover { text-decoration: underline; }

/* 自定义邮箱表单：服务器地址 + 端口并排显示 */
.form-row { display: flex; gap: var(--space-2); }
.form-row .input { flex: 1; min-width: 0; }
.port-input { width: 80px !important; flex: 0 0 80px !important; text-align: center; }

/* SMTP 加密方式下拉 */
.ssl-select {
  appearance: auto;
  cursor: pointer;
  padding-right: var(--space-3);
}

.btn-danger-text { color: var(--color-danger) !important; }
.btn-danger-text:hover { background: var(--color-danger-light) !important; }

/* ==================== 移动端适配 ==================== */
@media (max-width: 768px) {
  .account-page { padding: var(--space-4); }
  .toolbar { flex-direction: column; gap: var(--space-3); align-items: stretch; }
  .sort-toggle { justify-content: center; }
  .toggle-btn { flex: 1; text-align: center; padding: 8px 16px; }
  /* 添加账号对话框：两列布局 */
  .provider-grid { grid-template-columns: repeat(2, 1fr); }
  .edit-btn { opacity: 1; }
}
</style>
