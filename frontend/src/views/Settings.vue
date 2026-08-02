<template>
  <div class="settings-page">
  <!-- Gmail 网络代理配置：OAuth Client 密钥由 Cloudflare Broker 管理，本地只保留网络代理设置 -->
  <div class="provider-card">
  <button class="gmail-toggle" @click="proxyOpen = !proxyOpen">
  <div class="gmail-toggle-left">
  <div class="gmail-toggle-icon">
  <svg width="20" height="20" viewBox="0 0 48 48">
  <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
  <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
  <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
  <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
  </svg>
  </div>
  <div class="gmail-toggle-text">
  <span class="gmail-toggle-title">Gmail 网络代理</span>
  <span class="gmail-toggle-desc">用于 Gmail 收件、发件和 Broker token 刷新</span>
  </div>
  </div>
  <svg class="guide-arrow" :class="{ open: proxyOpen }" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="6 9 12 15 18 9"/>
  </svg>
  </button>

  <transition name="expand">
  <div v-if="proxyOpen" class="card-body">
  <div class="field proxy-field">
  <label class="field-label proxy-label">
  <label class="toggle-switch">
  <input type="checkbox" v-model="form.gmail_proxy_enabled" />
  <span class="toggle-slider"></span>
  </label>
  <span>启用 HTTP 代理</span>
  </label>
  <div class="field-input proxy-url-row" v-if="form.gmail_proxy_enabled">
  <input
  v-model="form.gmail_proxy_url"
  class="input"
  type="text"
  placeholder="http://127.0.0.1:7890"
  />
  <!-- 样式对齐「关于」页检测更新：圆角描边按钮，测试经代理到 Google 的连通性 -->
  <button
  type="button"
  class="check-proxy-btn"
  :disabled="proxyTesting || !form.gmail_proxy_url.trim()"
  :title="proxyTesting ? '正在测试...' : '测试代理与 Google 的连通性'"
  @click="testProxy"
  >
  <svg v-if="!proxyTesting" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
  </svg>
  <svg v-else class="spin-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21 12a9 9 0 11-6.219-8.56"/>
  </svg>
  <span>{{ proxyTesting ? '测试中' : '测试连通' }}</span>
  </button>
  </div>
  <transition name="fade">
  <span v-if="proxyTestMsg" class="status-msg" :class="proxyTestOk ? 'success' : 'error'" style="margin-top: 8px; display: inline-flex;">
  <svg v-if="proxyTestOk" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="20 6 9 17 4 12"/>
  </svg>
  <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
  </svg>
  {{ proxyTestMsg }}
  </span>
  </transition>
  <span class="field-hint">网络受限时启用，对 Gmail IMAP 收件、SMTP 发件、通过 Cloudflare Broker 刷新 token 生效。支持认证：http://user:pass@host:port</span>
  </div>

  <div class="save-bar">
  <button class="btn btn-primary btn-save" @click="saveSettings" :disabled="saving">
  <svg v-if="!saving" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>
  </svg>
  <span v-if="saving" class="saving-text">
  <span class="saving-dot"></span>
  保存中...
  </span>
  <span v-else>保存设置</span>
  </button>
  <transition name="fade">
  <span v-if="saveSuccess" class="status-msg success">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="20 6 9 17 4 12"/>
  </svg>
  保存成功
  </span>
  </transition>
  <transition name="fade">
  <span v-if="saveError" class="status-msg error">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
  </svg>
  {{ saveError }}
  </span>
  </transition>
  </div>
  </div>
  </transition>
  </div>

  <!-- ==================== 邮件备份配置（可折叠） ==================== -->
  <div class="provider-card">
  <button class="gmail-toggle backup-toggle" @click="backupOpen = !backupOpen">
  <div class="gmail-toggle-left">
  <div class="gmail-toggle-icon backup-toggle-icon">
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
  <polyline points="7 10 12 15 17 10"/>
  <line x1="12" y1="15" x2="12" y2="3"/>
  </svg>
  </div>
  <div class="gmail-toggle-text">
  <span class="gmail-toggle-title">邮件备份</span>
  <span class="gmail-toggle-desc">将邮件以 .eml 格式备份到飞牛OS 授权目录</span>
  </div>
  </div>
  <svg class="guide-arrow" :class="{ open: backupOpen }" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="6 9 12 15 18 9"/>
  </svg>
  </button>

  <transition name="expand">
  <div v-if="backupOpen" class="card-body">
  <!-- 总开关 -->
  <div class="field proxy-field">
  <label class="field-label proxy-label">
  <label class="toggle-switch">
  <input type="checkbox" v-model="backupForm.enabled" />
  <span class="toggle-slider"></span>
  </label>
  <span>启用自动备份</span>
  </label>
  <span class="field-hint">开启后，收件时自动将邮件归档为 .eml 文件保存到本地授权目录，防止邮件服务器删除后无法找回。</span>
  </div>

  <!-- 备份邮箱下拉多选 -->
  <div class="field" v-if="backupAccounts.length > 0" ref="backupSelectRef">
  <label class="field-label">备份邮箱</label>
  <div class="backup-multi-select" :class="{ disabled: !backupForm.enabled }">
  <!-- 触发器：点击展开/收起 -->
  <div class="select-trigger" @click="backupForm.enabled && (backupDropdownOpen = !backupDropdownOpen)">
  <!-- 已选邮箱标签 -->
  <div class="selected-tags" v-if="backupForm.account_ids.length > 0">
  <span v-for="id in backupForm.account_ids" :key="id" class="selected-tag">
  <span class="tag-icon" v-html="providerIcon(getAccountProvider(id))"></span>
  <span class="tag-text">{{ getAccountEmail(id) }}</span>
  <button
  class="tag-remove"
  @click.stop="toggleBackupAccount(id)"
  :disabled="!backupForm.enabled"
  >
  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
  </button>
  </span>
  </div>
  <!-- 占位文字 -->
  <span class="select-placeholder" v-else>请选择需要备份的邮箱</span>
  <!-- 下拉箭头 -->
  <svg class="select-arrow" :class="{ open: backupDropdownOpen }" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="6 9 12 15 18 9"/>
  </svg>
  </div>
  <!-- 下拉面板 -->
  <transition name="dropdown">
  <div class="select-dropdown" v-if="backupDropdownOpen">
  <label
  v-for="acc in backupAccounts"
  :key="acc.id"
  class="dropdown-item"
  :class="{ checked: backupForm.account_ids.includes(acc.id) }"
  >
  <input
  type="checkbox"
  :checked="backupForm.account_ids.includes(acc.id)"
  @change="toggleBackupAccount(acc.id)"
  />
  <span class="dropdown-icon" v-html="providerIcon(acc.provider)"></span>
  <span class="dropdown-email">{{ acc.email }}</span>
  </label>
  </div>
  </transition>
  </div>
  <span class="field-hint">仅备份选中邮箱账号的邮件，已选 {{ backupForm.account_ids.length }} 个。</span>
  </div>

  <!-- 备份位置选择（目录选择器弹窗） -->
  <div class="field">
  <label class="field-label">备份位置</label>
  <div class="field-input backup-path-row">
  <div class="backup-path-display" @click="backupForm.enabled && openBackupPathPicker()">
  <span class="backup-path-text" :class="{ 'path-empty': !backupForm.target_dir }">
  {{ backupForm.target_dir || '选择目录' }}
  </span>
  <button class="btn-browse" :disabled="!backupForm.enabled" @click.stop="openBackupPathPicker">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2f"/></svg>
  </button>
  </div>
  <button class="btn-refresh-paths" @click.stop="loadBackupAccessiblePaths" title="刷新授权目录">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
  <span>刷新</span>
  </button>
  </div>
  <span class="field-hint">选择邮件 .eml 文件的存储目录，必须为飞牛OS 授权目录。如无可用目录，请先在飞牛应用设置中为 FlyMail 授权目录后点击"刷新"。</span>
  </div>

  <!-- 保存按钮 -->
  <div class="save-bar">
  <button class="btn btn-primary btn-save" @click="saveBackupSettings" :disabled="backupSaving">
  <svg v-if="!backupSaving" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>
  </svg>
  <span v-if="backupSaving" class="saving-text">
  <span class="saving-dot"></span>
  保存中...
  </span>
  <span v-else>保存设置</span>
  </button>
  <transition name="fade">
  <span v-if="backupSuccess" class="status-msg success">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="20 6 9 17 4 12"/>
  </svg>
  保存成功
  </span>
  </transition>
  <transition name="fade">
  <span v-if="backupError" class="status-msg error">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
  </svg>
  {{ backupError }}
  </span>
  </transition>
  </div>
  </div>
  </transition>
  </div>


  <!-- ==================== 第三方通知设置（可折叠） ==================== -->
  <div class="provider-card">
  <button class="gmail-toggle notify-toggle" @click="notifyOpen = !notifyOpen">
  <div class="gmail-toggle-left">
  <div class="gmail-toggle-icon notify-toggle-icon">
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
  <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
  </svg>
  </div>
  <div class="gmail-toggle-text">
  <span class="gmail-toggle-title">通知设置</span>
  <span class="gmail-toggle-desc">推送到 Bark、Telegram、Webhook 等</span>
  </div>
  </div>
  <svg class="guide-arrow" :class="{ open: notifyOpen }" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="6 9 12 15 18 9"/>
  </svg>
  </button>

  <transition name="expand">
  <div v-if="notifyOpen" class="card-body">
  <!-- 全局设置 -->
  <div class="notify-section" :class="{ disabled: false }">
  <div class="field proxy-field">
  <label class="field-label proxy-label">
  <label class="toggle-switch">
  <input type="checkbox" v-model="notifyForm.enabled" />
  <span class="toggle-slider"></span>
  </label>
  <span>启用第三方通知</span>
  </label>
  <span class="field-hint">开启后，新邮件将按下方配置推送到外部渠道。</span>
  </div>

  <!-- 免打扰 + 通知模式：同一行左右排布 -->
  <div class="notify-inline-row" :class="{ 'notify-dim': !notifyForm.enabled }">
  <div class="field notify-inline-field notify-inline-dnd">
  <label class="field-label">免打扰时段</label>
  <div class="notify-dnd-row">
  <input class="input notify-time" type="time" v-model="notifyForm.dnd_start" :disabled="!notifyForm.enabled" />
  <span class="notify-dnd-sep">至</span>
  <input class="input notify-time" type="time" v-model="notifyForm.dnd_end" :disabled="!notifyForm.enabled" />
  </div>
  <span class="field-hint">默认 21:00–07:00（跨午夜）；起止相同=关闭免打扰</span>
  </div>

  <div class="field notify-inline-field notify-inline-mode">
  <label class="field-label">通知模式</label>
  <div class="notify-segment" role="group" aria-label="通知模式">
  <button
  type="button"
  class="notify-segment-item"
  :class="{ active: notifyForm.mode === 'text' }"
  :disabled="!notifyForm.enabled"
  @click="notifyForm.mode = 'text'"
  >文字</button>
  <button
  type="button"
  class="notify-segment-item"
  :class="{ active: notifyForm.mode === 'image' }"
  :disabled="!notifyForm.enabled"
  @click="notifyForm.mode = 'image'"
  >图片</button>
  </div>
  <span class="field-hint">图片：Telegram / 企微 Webhook 直传；Bark / 钉钉 / 飞书需图床</span>
  </div>
  </div>

  <!-- 全局 Cloudflare 图床：图片模式且需公网 URL 的渠道共用 -->
  <div class="notify-imgbed" :class="{ 'notify-dim': !notifyForm.enabled }">
  <div class="notify-imgbed-head">
  <div class="notify-imgbed-title-row">
  <div class="notify-imgbed-title">Cloudflare 图床</div>
  <a
  class="cf-deploy-btn"
  :href="notifyForm.imgbed_deploy_url || defaultImgbedDeployUrl"
  target="_blank"
  rel="noopener noreferrer"
  title="Deploy to Cloudflare"
  >
  <svg class="cf-deploy-cloud" viewBox="0 0 16 10" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path fill="#F6821F" d="M12.6 4.2c-.15-1.55-1.45-2.75-3.05-2.75-.8 0-1.52.3-2.05.8C6.95 1.15 5.75.25 4.35.25 2.35.25.75 1.8.65 3.75.15 3.95-.1 4.45-.1 5.05c0 1.2 1 2.2 2.2 2.2h9.1c1.05 0 1.9-.85 1.9-1.9 0-1-.75-1.85-1.65-2.05.05-.03.1-.06.15-.1z"/>
  <path fill="#FBAD41" d="M11.55 4.55c-.1-1.05-.95-1.85-2.05-1.85-.55 0-1.05.2-1.4.55-.4-.7-1.15-1.15-2.05-1.15-1.3 0-2.35 1.05-2.4 2.35-.75.2-1.3.85-1.3 1.65 0 .95.8 1.75 1.75 1.75h7.05c.85 0 1.55-.7 1.55-1.55 0-.8-.6-1.45-1.35-1.55.05-.07.1-.14.2-.2z"/>
  </svg>
  <span class="cf-deploy-text">Deploy to Cloudflare</span>
  </a>
  </div>
  <span class="field-hint notify-imgbed-desc">图片通知：Bark / 钉钉 / 飞书需图床；Telegram / 企业微信可直传</span>
  </div>
  <div class="notify-inline-row notify-imgbed-fields">
  <div class="field notify-inline-field">
  <label class="field-label">图床地址</label>
  <input
  class="input"
  type="text"
  v-model="notifyForm.imgbed.base_url"
  placeholder="https://flymail-imgbed.xxx.workers.dev"
  :disabled="!notifyForm.enabled"
  />
  </div>
  <div class="field notify-inline-field">
  <label class="field-label">上传密钥</label>
  <div class="notify-secret-row notify-secret-row-full">
  <input
  class="input"
  :type="notifyImgbedTokenVisible ? 'text' : 'password'"
  v-model="notifyForm.imgbed.upload_token"
  placeholder="Cloudflare UPLOAD_TOKEN"
  :disabled="!notifyForm.enabled"
  autocomplete="off"
  />
  <button type="button" class="btn-secret-toggle" @click="notifyImgbedTokenVisible = !notifyImgbedTokenVisible" :title="notifyImgbedTokenVisible ? '隐藏' : '显示'">
  <svg v-if="!notifyImgbedTokenVisible" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
  <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
  </button>
  </div>
  </div>
  </div>
  <div class="notify-test-row">
  <button
  type="button"
  class="check-proxy-btn"
  :disabled="!notifyForm.enabled || notifyImgbedBusy || !notifyForm.imgbed.base_url.trim() || !notifyForm.imgbed.upload_token.trim()"
  @click="testImgbed"
  >
  <svg v-if="!notifyImgbedBusy || notifyImgbedAction !== 'test'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
  <svg v-else class="spin-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
  <span>{{ notifyImgbedBusy && notifyImgbedAction === 'test' ? '测试中' : '测试上传' }}</span>
  </button>
  <button
  type="button"
  class="check-proxy-btn notify-purge-btn"
  :disabled="!notifyForm.enabled || notifyImgbedBusy || !notifyForm.imgbed.base_url.trim() || !notifyForm.imgbed.upload_token.trim()"
  @click="purgeImgbed"
  >
  <svg v-if="!notifyImgbedBusy || notifyImgbedAction !== 'purge'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
  <svg v-else class="spin-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
  <span>{{ notifyImgbedBusy && notifyImgbedAction === 'purge' ? '清理中' : '清理图床' }}</span>
  </button>
  <transition name="fade">
  <span v-if="notifyImgbedMsg" class="status-msg" :class="notifyImgbedOk ? 'success' : 'error'">
  {{ notifyImgbedMsg }}
  <a v-if="notifyImgbedOk && notifyImgbedPreviewUrl" :href="notifyImgbedPreviewUrl" target="_blank" rel="noopener" class="notify-imgbed-link">查看图片</a>
  </span>
  </transition>
  </div>
  </div>

  </div>

  <!-- 渠道：横向 Tab（对齐邮件配置教程） -->
  <div class="notify-channels">
  <div class="guide-tabs notify-guide-tabs">
  <button
  type="button"
  class="guide-tab"
  :class="{ active: notifyChannelTab === 'bark' }"
  @click="notifyChannelTab = 'bark'"
  >
  <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg" width="16" height="16">
  <path d="M198.567436 0h624.044321c104.527424 21.308277 170.715834 83.712709 198.559557 187.213296v646.736843c-26.476499 98.332366-88.880931 160.736798-187.213296 187.213296h-646.736842c-103.500587-27.843723-165.905019-94.032133-187.213297-198.559557v-624.044321c22.692521-109.678626 88.880931-175.867036 198.559557-198.559557z" fill="#FF3A2F" opacity=".996"/>
  <path d="M187.221176 351.734072a1769.279114 1769.279114 0 0 1 158.847645 48.221607 1346.738704 1346.738704 0 0 1 2.836565 212.742382 3639.029363 3639.029363 0 0 1-153.174515 56.731302c-10.733562-1.571457-18.295845-7.244587-22.692521-17.019391a3546.948787 3546.948787 0 0 1 0-283.656509 59.687003 59.687003 0 0 0 14.182826-17.019391z" fill="#FFFAFA"/>
  <path d="M805.592367 357.407202c16.253518-2.524543 30.436343 1.253762 42.548476 11.346261 3.783978 96.443213 3.783978 192.886427 0 289.329639-5.423512 7.908343-12.985795 11.692321-22.69252 11.346261a862.542715 862.542715 0 0 1-147.501385-45.385042 2048.397119 2048.397119 0 0 1 0-215.578947 1786.877163 1786.877163 0 0 1 127.645429-51.058172z" fill="#FFFCFC"/>
  <path d="M136.163004 402.792244a871.557319 871.557319 0 0 1 0 198.559557c-24.530615-52.856554-49.117961-105.803878-73.750693-158.847646 0.164521-8.679889 3.942825-15.294759 11.346261-19.855956a239.973407 239.973407 0 0 1 62.404432-19.855955zM885.01619 419.811634a6240.102825 6240.102825 0 0 1 73.750692 161.684211 35.701008 35.701008 0 0 1-5.67313 17.01939 1689.157496 1689.157496 0 0 0-73.750693 25.529086c-1.860787-69.08738 0.028366-137.164942 5.673131-204.232687z" fill="#FFFAF9"/>
  <path d="M646.744721 442.504155h-266.637119v141.828255h266.637119a3271.246006 3271.246006 0 0 1-272.310249 5.67313v-153.174515c91.762881-1.872133 182.532964 0.022693 272.310249 5.67313z" fill="#FFB9B4"/>
  <path d="M646.744721 442.504155v141.828255h-266.637119v-141.828255h266.637119z" fill="#FFFEFD"/>
  <path d="M136.163004 402.792244c0.340388-3.08051 2.22954-4.969662 5.67313-5.67313a973.679335 973.679335 0 0 1 0 209.905817c-3.44359-0.703468-5.332742-2.59262-5.67313-5.67313a871.557319 871.557319 0 0 0 0-198.559557z" fill="#FF9993"/>
  <path d="M885.01619 419.811634c-5.644765 67.067745-7.533917 135.145307-5.673131 204.232687-7.516898-69.059014-7.516898-139.025729 0-209.905817 3.44359 0.703468 5.332742 2.59262 5.673131 5.67313z" fill="#FF857E"/>
  </svg>
  <span class="tab-label">Bark</span>
  </button>
  <button
  type="button"
  class="guide-tab"
  :class="{ active: notifyChannelTab === 'telegram' }"
  @click="notifyChannelTab = 'telegram'"
  >
  <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg" width="16" height="16">
  <path d="M679.424 746.862l84.005-395.996c7.424-34.852-12.581-48.567-35.438-40.009L234.277 501.138c-33.72 13.13-33.134 32-5.706 40.558l126.282 39.424 293.156-184.576c13.714-9.143 26.295-3.986 16.018 5.157L426.898 615.973l-9.143 130.304c13.13 0 18.871-5.706 25.71-12.581l61.696-59.429 128 94.282c23.442 13.129 40.01 6.29 46.3-21.724zM1024 512c0 282.843-229.157 512-512 512S0 794.843 0 512 229.157 0 512 0s512 229.157 512 512z" fill="#1296DB"/>
  </svg>
  <span class="tab-label">Telegram</span>
  </button>
  <button
  type="button"
  class="guide-tab"
  :class="{ active: notifyChannelTab === 'webhook' }"
  @click="notifyChannelTab = 'webhook'"
  >
  <svg viewBox="0 0 1126 1024" xmlns="http://www.w3.org/2000/svg" width="16" height="16">
  <path d="M475.854144 913.399911c-83.761992 116.529989-247.395976 145.763986-365.666965 64.715993-117.655989-81.099992-145.252986-242.480976-62.564994-360.137964a264.700974 264.700974 0 0 1 205.51498-111.460989l2.918 80.484992a182.679982 182.679982 0 0 0-135.422987 76.491992c-57.445994 81.049992-39.679996 190.154981 39.064996 244.733976 79.154992 54.015995 189.949981 33.279997 247.344976-47.205995a186.468982 186.468982 0 0 0 32.204997-81.048992v-56.881995l320.252969-2.303999 3.941999-6.144a109.566989 109.566989 0 0 1 148.069986-40.498996 105.82999 105.82999 0 0 1 39.063996 146.276986 110.385989 110.385989 0 0 1-148.631985 39.935996 99.68499 99.68499 0 0 1-47.614996-57.496994l-233.572977 1.176999A278.269973 278.269973 0 0 1 475.854144 913.399911z m417.787959-401.659961c145.252986 17.406998 248.522976 145.149986 230.756977 285.231972-17.766998 140.644986-149.809985 240.124977-294.959971 222.717978a266.083974 266.083974 0 0 1-196.862981-124.261987l71.115993-40.446996a185.546982 185.546982 0 0 0 133.118987 81.611992c100.45299 11.775999 189.335982-55.141995 201.367981-148.989986 12.082999-94.053991-59.032994-180.017982-158.359985-191.844981a199.677981 199.677981 0 0 0-87.807991 10.085999l-48.639996 24.575997-148.119985-268.285973h-12.645999c-60.107994-1.69-107.569989-50.789995-106.18699-109.71999 1.74-58.469994 53.349995-104.08899 113.662989-101.78499 60.260994 3.328 108.029989 51.199995 106.23899 109.71999a104.03699 104.03699 0 0 1-26.419997 64.665993l109.003989 197.373981a278.524973 278.524973 0 0 1 114.686989-10.649999zM348.931156 358.651965A255.126975 255.126975 0 0 1 484.968143 20.119998c133.220987-55.140995 287.023972 7.321999 344.469966 139.519986a254.205975 254.205975 0 0 1-11.467999 228.911978l-71.218993-40.447996c24.063998-45.566996 28.056997-101.21999 5.12-153.597985-39.064996-90.008991-142.948986-133.374987-231.933978-96.766991-89.598991 37.119996-129.739987 140.644986-90.622991 230.653978 15.973998 37.119996 43.007996 65.790994 75.774993 84.939992l22.322997 11.775998-176.125982 280.777973c1.74 2.867 3.942 6.143999 5.733999 10.649999 28.057997 51.249995 8.652999 115.914989-44.235996 143.408986-52.274995 27.544997-118.269988 7.372999-146.942985-45.515996a105.87999 105.87999 0 0 1 44.236995-144.536985 102.91099 102.91099 0 0 1 70.654994-9.522999L413.34015 448.302956a248.829976 248.829976 0 0 1-64.409994-89.599991z" fill="#6366F1"/>
  </svg>
  <span class="tab-label">Webhook</span>
  </button>
  </div>

  <div class="notify-channel-panel">
  <!-- Bark -->
  <div v-if="notifyChannelTab === 'bark'" class="guide-panel">
  <div class="field proxy-field">
  <label class="field-label proxy-label">
  <label class="toggle-switch">
  <input type="checkbox" v-model="notifyForm.bark.enabled" :disabled="!notifyForm.enabled" />
  <span class="toggle-slider"></span>
  </label>
  <span>启用 Bark</span>
  </label>
  </div>
  <div class="notify-inline-row" :class="{ 'notify-dim': !notifyForm.bark.enabled || !notifyForm.enabled }">
  <div class="field notify-inline-field">
  <label class="field-label">Server</label>
  <input
  class="input"
  type="text"
  v-model="notifyForm.bark.server"
  placeholder="https://api.day.app"
  :disabled="!notifyForm.enabled || !notifyForm.bark.enabled"
  />
  <span class="field-hint">须与 Bark App 服务器一致；默认 api.day.app</span>
  </div>
  <div class="field notify-inline-field">
  <label class="field-label">Device Key</label>
  <div class="notify-secret-row notify-secret-row-full">
  <input
  class="input"
  :type="notifyBarkKeyVisible ? 'text' : 'password'"
  v-model="notifyForm.bark.device_key"
  placeholder="Bark App 中复制 Device Key"
  :disabled="!notifyForm.enabled || !notifyForm.bark.enabled"
  autocomplete="off"
  />
  <button type="button" class="btn-secret-toggle" @click="notifyBarkKeyVisible = !notifyBarkKeyVisible" :title="notifyBarkKeyVisible ? '隐藏' : '显示'">
  <svg v-if="!notifyBarkKeyVisible" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
  <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
  </button>
  </div>
  </div>
  </div>

  <div class="notify-test-row">
  <button
  type="button"
  class="check-proxy-btn"
  :disabled="notifyTesting || !notifyForm.bark.device_key.trim()"
  @click="testNotifyChannel('bark')"
  >
  <svg v-if="!notifyTesting || notifyTestingChannel !== 'bark'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/>
  </svg>
  <svg v-else class="spin-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
  <span>{{ notifyTesting && notifyTestingChannel === 'bark' ? '测试中' : '发送测试' }}</span>
  </button>
  <transition name="fade">
  <span v-if="notifyTestMsg && notifyTestingChannel === 'bark'" class="status-msg" :class="notifyTestOk ? 'success' : 'error'">
  {{ notifyTestMsg }}
  </span>
  </transition>
  </div>
  </div>

  <!-- Telegram -->
  <div v-if="notifyChannelTab === 'telegram'" class="guide-panel">
  <div class="notify-inline-row notify-toggle-pair">
  <div class="field proxy-field notify-inline-field">
  <label class="field-label proxy-label">
  <label class="toggle-switch">
  <input type="checkbox" v-model="notifyForm.telegram.enabled" :disabled="!notifyForm.enabled" />
  <span class="toggle-slider"></span>
  </label>
  <span>启用 Telegram</span>
  </label>
  </div>
  <div class="field proxy-field notify-inline-field" :class="{ 'notify-dim': !notifyForm.telegram.enabled || !notifyForm.enabled }">
  <label class="field-label proxy-label">
  <label class="toggle-switch">
  <input type="checkbox" v-model="notifyForm.telegram.use_gmail_proxy" :disabled="!notifyForm.enabled || !notifyForm.telegram.enabled" />
  <span class="toggle-slider"></span>
  </label>
  <span>使用 Gmail 网络代理</span>
  </label>
  </div>
  </div>
  <span
  v-if="notifyForm.telegram.use_gmail_proxy && !form.gmail_proxy_enabled && notifyForm.telegram.enabled"
  class="field-hint notify-warn-hint"
  >当前未启用 Gmail 网络代理，请先在顶部卡片配置并测试连通。</span>
  <div class="notify-inline-row" :class="{ 'notify-dim': !notifyForm.telegram.enabled || !notifyForm.enabled }">
  <div class="field notify-inline-field">
  <label class="field-label">Bot Token</label>
  <div class="notify-secret-row notify-secret-row-full">
  <input
  class="input"
  :type="notifyTgTokenVisible ? 'text' : 'password'"
  v-model="notifyForm.telegram.bot_token"
  placeholder="123456:ABC..."
  :disabled="!notifyForm.enabled || !notifyForm.telegram.enabled"
  autocomplete="off"
  />
  <button type="button" class="btn-secret-toggle" @click="notifyTgTokenVisible = !notifyTgTokenVisible">
  <svg v-if="!notifyTgTokenVisible" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
  <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
  </button>
  </div>
  </div>
  <div class="field notify-inline-field">
  <label class="field-label">Chat ID</label>
  <input
  class="input"
  type="text"
  v-model="notifyForm.telegram.chat_id"
  placeholder="用户 / 群 / 频道 ID"
  :disabled="!notifyForm.enabled || !notifyForm.telegram.enabled"
  />
  </div>
  </div>
  <div class="notify-test-row">
  <button
  type="button"
  class="check-proxy-btn"
  :disabled="notifyTesting || !notifyForm.telegram.bot_token.trim() || !notifyForm.telegram.chat_id.trim()"
  @click="testNotifyChannel('telegram')"
  >
  <svg v-if="!notifyTesting || notifyTestingChannel !== 'telegram'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/>
  </svg>
  <svg v-else class="spin-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
  <span>{{ notifyTesting && notifyTestingChannel === 'telegram' ? '测试中' : '发送测试' }}</span>
  </button>
  <transition name="fade">
  <span v-if="notifyTestMsg && notifyTestingChannel === 'telegram'" class="status-msg" :class="notifyTestOk ? 'success' : 'error'">
  {{ notifyTestMsg }}
  </span>
  </transition>
  </div>
  </div>

  <!-- Webhook -->
  <div v-if="notifyChannelTab === 'webhook'" class="guide-panel">
  <div class="notify-inline-row notify-toggle-pair">
  <div class="field proxy-field notify-inline-field">
  <label class="field-label proxy-label">
  <label class="toggle-switch">
  <input type="checkbox" v-model="notifyForm.webhook.enabled" :disabled="!notifyForm.enabled" />
  <span class="toggle-slider"></span>
  </label>
  <span>启用 Webhook</span>
  </label>
  </div>
  <div class="field proxy-field notify-inline-field" :class="{ 'notify-dim': !notifyForm.webhook.enabled || !notifyForm.enabled }">
  <label class="field-label proxy-label">
  <label class="toggle-switch">
  <input type="checkbox" v-model="notifyForm.webhook.use_gmail_proxy" :disabled="!notifyForm.enabled || !notifyForm.webhook.enabled" />
  <span class="toggle-slider"></span>
  </label>
  <span>使用 Gmail 网络代理</span>
  </label>
  </div>
  </div>
  <span
  v-if="notifyForm.webhook.use_gmail_proxy && !form.gmail_proxy_enabled && notifyForm.webhook.enabled"
  class="field-hint notify-warn-hint"
  >当前未启用 Gmail 网络代理，请先在顶部卡片配置并测试连通。</span>
  <div class="notify-inline-row" :class="{ 'notify-dim': !notifyForm.webhook.enabled || !notifyForm.enabled }">
  <div class="field notify-inline-field">
  <label class="field-label">URL</label>
  <input
  class="input"
  type="text"
  v-model="notifyForm.webhook.url"
  placeholder="企微 / 钉钉 / 飞书机器人地址，或其它 https://.../hook"
  :disabled="!notifyForm.enabled || !notifyForm.webhook.enabled"
  />
  <span class="field-hint">自动识别企微 / 钉钉 / 飞书；其它地址走通用 JSON</span>
  </div>
  <div class="field notify-inline-field">
  <label class="field-label">密钥（可选）</label>
  <div class="notify-secret-row notify-secret-row-full">
  <input
  class="input"
  :type="notifyWhSecretVisible ? 'text' : 'password'"
  v-model="notifyForm.webhook.secret"
  placeholder="通用 Bearer；钉钉/飞书填加签密钥；企微可不填"
  :disabled="!notifyForm.enabled || !notifyForm.webhook.enabled"
  autocomplete="off"
  />
  <button type="button" class="btn-secret-toggle" @click="notifyWhSecretVisible = !notifyWhSecretVisible">
  <svg v-if="!notifyWhSecretVisible" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
  <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
  </button>
  </div>
  </div>
  </div>
  <div class="notify-test-row">
  <button
  type="button"
  class="check-proxy-btn"
  :disabled="notifyTesting || !notifyForm.webhook.url.trim()"
  @click="testNotifyChannel('webhook')"
  >
  <svg v-if="!notifyTesting || notifyTestingChannel !== 'webhook'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/>
  </svg>
  <svg v-else class="spin-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
  <span>{{ notifyTesting && notifyTestingChannel === 'webhook' ? '测试中' : '发送测试' }}</span>
  </button>
  <transition name="fade">
  <span v-if="notifyTestMsg && notifyTestingChannel === 'webhook'" class="status-msg" :class="notifyTestOk ? 'success' : 'error'">
  {{ notifyTestMsg }}
  </span>
  </transition>
  </div>
  </div>
  </div>
  </div>

  <div class="save-bar">
  <button class="btn btn-primary btn-save" @click="saveNotifySettings" :disabled="notifySaving">
  <svg v-if="!notifySaving" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>
  </svg>
  <span v-if="notifySaving" class="saving-text">
  <span class="saving-dot"></span>
  保存中...
  </span>
  <span v-else>保存设置</span>
  </button>
  <transition name="fade">
  <span v-if="notifySuccess" class="status-msg success">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="20 6 9 17 4 12"/>
  </svg>
  保存成功
  </span>
  </transition>
  <transition name="fade">
  <span v-if="notifyError" class="status-msg error">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
  </svg>
  {{ notifyError }}
  </span>
  </transition>
  </div>

  </div>
  </transition>
  </div>

  <!-- ==================== MCP 服务器设置（可折叠） ==================== -->
  <div class="provider-card">
  <button class="gmail-toggle" @click="mcpOpen = !mcpOpen">
  <div class="gmail-toggle-left">
  <div class="gmail-toggle-icon" style="background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%); color: #2E7D32;">
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1.27A7.01 7.01 0 0 1 14 22h-4a7.01 7.01 0 0 1-6.73-5H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2z"/>
  <path d="M9 15v1"/><path d="M15 15v1"/><path d="M9 11v1"/><path d="M15 11v1"/>
  </svg>
  </div>
  <div class="gmail-toggle-text">
  <span class="gmail-toggle-title">MCP Server</span>
  <span class="gmail-toggle-desc">AI 助手接入 — 通过 MCP 协议让 AI 读取邮件、搜索联系人</span>
  </div>
  </div>
  <svg class="guide-arrow" :class="{ open: mcpOpen }" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="6 9 12 15 18 9"/>
  </svg>
  </button>

  <transition name="expand">
  <div v-if="mcpOpen" class="card-body">
  <!-- 启用开关 -->
  <div class="field proxy-field">
  <label class="field-label proxy-label">
  <label class="toggle-switch">
  <input type="checkbox" v-model="mcpForm.enabled" />
  <span class="toggle-slider"></span>
  </label>
  <span>启用 MCP 服务器</span>
  </label>
  <span class="field-hint">开启后，AI 助手可通过 Bearer Token 连接 MCP 服务读取邮件数据。</span>
  </div>

  <!-- 端口 -->
  <div class="field" :class="{ 'notify-dim': !mcpForm.enabled }">
  <label class="field-label">端口</label>
  <input
  class="input"
  type="number"
  v-model.number="mcpForm.port"
  min="1024"
  max="65535"
  :disabled="!mcpForm.enabled"
  style="max-width: 160px;"
  />
  <span class="field-hint">子应用挂载模式自动使用主应用端口，此端口仅独立运行（python -m flymail_mcp.server）时生效。</span>
  </div>

  <!-- 认证令牌 -->
  <div class="field" :class="{ 'notify-dim': !mcpForm.enabled }">
  <label class="field-label">认证令牌</label>
  <div class="field-input proxy-url-row" style="max-width: 600px;">
  <input
  class="input"
  :type="mcpTokenVisible ? 'text' : 'password'"
  v-model="mcpForm.token_display"
  :placeholder="mcpForm.has_token ? '••••••••••••••••' : '启用后自动生成'"
  :disabled="!mcpForm.enabled"
  readonly
  autocomplete="off"
  />
  <button
  type="button"
  class="btn-secret-toggle"
  @click="mcpTokenVisible = !mcpTokenVisible"
  :title="mcpTokenVisible ? '隐藏' : '显示'"
  :disabled="!mcpForm.enabled || !mcpForm.has_token"
  >
  <svg v-if="!mcpTokenVisible" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
  <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
  </button>
  <button
  type="button"
  class="check-proxy-btn"
  :disabled="!mcpForm.enabled || !mcpForm.has_token"
  @click="copyMcpToken"
  title="复制令牌"
  >
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
  <span>{{ mcpCopied ? '已复制' : '复制' }}</span>
  </button>
  <button
  type="button"
  class="check-proxy-btn"
  :disabled="!mcpForm.enabled"
  @click="regenerateMcpToken"
  title="刷新令牌"
  >
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
  <span>刷新</span>
  </button>
  </div>
  <span class="field-hint">AI 助手通过此 Bearer Token 连接 MCP 服务。刷新后旧令牌立即失效。</span>
  </div>

  <!-- 连接方式说明 -->
  <div class="guide-section" style="margin-bottom: 0;">
  <div class="guide-body" style="border-top: none; padding: 0;">
  <div class="guide-content" style="padding: 12px 0;">
  <div style="font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 8px;">连接方式</div>
  <div class="guide-tabs" style="padding: 0; background: transparent; margin-bottom: 8px;">
  <button
  class="guide-tab"
  :class="{ active: mcpGuideTab === 'claude' }"
  @click="mcpGuideTab = 'claude'"
  >Claude Desktop</button>
  <button
  class="guide-tab"
  :class="{ active: mcpGuideTab === 'curl' }"
  @click="mcpGuideTab = 'curl'"
  >cURL 测试</button>
  </div>
  <div v-if="mcpGuideTab === 'claude'" class="guide-panel" style="padding: 0;">
  <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 6px;">在 Claude Desktop 的配置文件中添加：</div>
  <pre class="mcp-config-code" style="margin: 0;">{
  "mcpServers": {
    "flymail": {
      "url": "http://localhost:{{ mcpForm.port || 8080 }}/mcp/sse",
      "headers": {
        "Authorization": "Bearer {{ mcpForm.has_token ? '...' : '<your-token>' }}"
      }
    }
  }
}</pre>
  </div>
  <div v-if="mcpGuideTab === 'curl'" class="guide-panel" style="padding: 0;">
  <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 6px;">使用 cURL 测试 MCP 连接：</div>
  <pre class="mcp-config-code" style="margin: 0;"># 建立 SSE 连接
curl -N -H "Authorization: Bearer &lt;token&gt;" \
  http://localhost:{{ mcpForm.port || 8080 }}/mcp/sse

# 发送 JSON-RPC 请求（新终端）
curl -X POST \
  -H "Authorization: Bearer &lt;token&gt;" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
  http://localhost:{{ mcpForm.port || 8080 }}/mcp/messages/</pre>
  </div>
  <!-- 状态指示 -->
  <div class="mcp-status">
  <span class="mcp-status-dot" :class="{ 'status-ok': mcpForm.enabled, 'status-off': !mcpForm.enabled }"></span>
  <span>{{ mcpForm.enabled ? '运行中' : '已停止' }} · 端口 {{ mcpForm.port || 8080 }}</span>
  </div>
  </div>
  </div>
  </div>

  <!-- 保存按钮 -->
  <div class="save-bar">
  <button class="btn btn-primary btn-save" @click="saveMcpSettings" :disabled="mcpSaving">
  <svg v-if="!mcpSaving" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>
  </svg>
  <span v-if="mcpSaving" class="saving-text">
  <span class="saving-dot"></span>
  保存中...
  </span>
  <span v-else>保存设置</span>
  </button>
  <transition name="fade">
  <span v-if="mcpSuccess" class="status-msg success">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="20 6 9 17 4 12"/>
  </svg>
  保存成功
  </span>
  </transition>
  <transition name="fade">
  <span v-if="mcpError" class="status-msg error">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
  </svg>
  {{ mcpError }}
  </span>
  </transition>
  </div>
  </div>
  </transition>
  </div>

  <!-- ==================== 配置教程（可折叠） ==================== -->
  <div class="guide-section">
  <!-- 折叠按钮 -->
  <button class="guide-toggle" @click="guideOpen = !guideOpen">
  <div class="guide-toggle-left">
  <div class="guide-toggle-icon">
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
  </svg>
  </div>
  <div class="guide-toggle-text">
  <span class="guide-toggle-title">邮箱配置教程</span>
  <span class="guide-toggle-desc">按步骤开启邮箱服务并获取授权凭据</span>
  </div>
  </div>
  <svg class="guide-arrow" :class="{ open: guideOpen }" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="6 9 12 15 18 9"/>
  </svg>
  </button>

  <!-- 折叠内容 -->
  <transition name="expand">
  <div v-if="guideOpen" class="guide-body">
  <!-- 平台 Tab 切换 -->
  <div class="guide-tabs">
  <button
  class="guide-tab"
  :class="{ active: activeTab === 'qq' }"
  @click="activeTab = 'qq'"
  >
  <svg width="16" height="16" viewBox="0 0 1024 1024"><path d="M211.101867 363.776c-14.933333 66.56-7.466667 133.12 7.466666 192.256 14.933333 51.754667-7.466667 103.509333-52.309333 133.077333-67.285333 36.949333-149.461333-14.805333-156.970667-81.322666C-57.954133 260.266667 255.944533-57.642667 614.728533 8.874667c-209.28 22.186667-366.250667 162.688-403.626666 354.901333z" fill="#FFDC04"/><path d="M532.4672 844.373333c59.818667-22.186667 119.594667-59.136 164.437333-103.509333 37.376-36.992 97.152-44.373333 141.994667-14.805333 67.285333 36.992 67.285333 133.12 7.509333 177.493333-269.098667 229.162667-702.549333 118.272-822.186666-221.866667 112.128 162.688 321.408 221.866667 508.245333 162.688z" fill="#E03A22"/><path d="M794.056533 326.826667a425.173333 425.173333 0 0 0-171.861333-88.746667c-52.352-14.762667-89.728-59.136-89.728-110.933333 0-73.898667 82.218667-125.653333 149.504-96.085334 336.341333 118.314667 455.893333 539.733333 216.746667 813.312 89.685333-177.493333 37.376-391.850667-104.661334-517.546666z" fill="#27AA3A"/><path d="M652.104533 489.472c0-14.805333 0-29.568-7.509333-36.949333 0-7.424 0-7.424-7.466667-14.805334 0-73.941333-44.842667-133.12-127.061333-133.12-82.218667 0-127.061333 59.178667-127.061333 133.12 0 7.381333-7.466667 7.381333-7.466667 14.805334-7.466667 14.762667-7.466667 22.186667-7.466667 29.568v7.381333c-14.933333 7.381333-29.909333 29.568-37.376 51.754667-14.933333 36.949333-14.933333 73.941333-7.466666 73.941333 7.466667 7.381333 22.4-7.381333 37.333333-22.186667 0 22.186667 14.933333 44.373333 29.909333 59.136-14.933333 0-29.866667 14.805333-29.866666 29.568 0 22.186667 29.866667 36.992 74.709333 36.992 37.376 0 67.285333-14.805333 74.752-29.568h7.466667c7.466667 14.762667 37.376 29.568 74.752 29.568s74.752-14.805333 74.752-36.992c0-14.762667-14.933333-22.186667-29.909334-29.568 14.933333-14.762667 29.866667-29.568 37.376-51.754666 14.933333 22.186667 29.866667 29.568 37.376 22.186666 14.933333-7.381333 7.466667-36.949333-7.466667-73.941333-7.466667-22.186667-22.4-44.373333-37.376-51.754667v-7.381333z" fill="#2B2B2B"/></svg>
  <span class="tab-label">腾讯邮箱</span>
  </button>
  <button
  class="guide-tab"
  :class="{ active: activeTab === 'netease' }"
  @click="activeTab = 'netease'"
  >
  <svg width="16" height="16" viewBox="0 0 1024 1024"><path d="M592.298667 661.76c60.458667-47.573333 67.072-49.92 84.992-27.392 15.573333 19.242667 12.245333 22.741333-91.733334 113.365333-34.688 30.592-63.744 62.293333-63.744 71.381334 0 7.936-8.96 14.762667-19.029333 14.762666-10.026667 0-46.933333 19.285333-81.493333 44.288C353.024 926.890667 227.84 981.333333 184.192 981.333333c-71.466667 0-67.072-71.381333 5.632-91.733333 124.117333-34.090667 251.605333-106.581333 402.432-227.84z m-46.848-200.618667c14.506667-5.717333 39.125333-7.978667 54.826666-5.589333 15.573333 1.109333 51.370667 5.674667 80.426667 9.045333 128.512 14.805333 224.64 132.693333 214.613333 259.626667-5.546667 70.229333-24.576 106.538667-81.578666 158.634667-89.514667 81.536-214.698667 121.216-257.109334 82.688-27.989333-26.112-50.304-81.706667-41.344-103.210667 5.546667-15.914667 10.069333-15.914667 41.344 1.152 70.4 36.266667 171.008-2.261333 229.12-87.296 58.154667-86.186667 33.493333-180.266667-46.933333-180.266667-29.056 0-40.234667-6.741333-51.370667-31.701333-21.333333-44.16-63.744-46.378667-111.829333-4.48-223.530667 196.053333-431.488 302.592-478.421333 245.930667-30.165333-36.224-6.741333-54.357333 117.333333-90.666667 42.538667-12.544 112.938667-49.834667 191.146667-103.168 111.786667-74.752 124.074667-86.058667 119.68-112.170667-4.522667-21.504 0-30.592 20.096-38.528z m-191.146667-410.282666c60.330667-12.458667 257.024-10.24 307.370667 3.328 95.061333 25.002667 110.634667 41.941333 138.666666 160 16.725333 70.272 15.616 101.973333-4.522666 150.698666-22.314667 55.594667-64.853333 69.12-201.216 68.010667-109.610667-1.109333-111.786667 0-130.816 29.44-23.509333 38.442667-118.570667 114.432-160.981334 130.346667-128.512 46.378667-200.106667 50.944-211.285333 14.677333-11.136-35.2 13.397333-56.704 66.005333-56.704 65.834667 0 174.336-44.245333 205.610667-82.773333 12.245333-13.568 4.437333-17.066667-48.085333-21.546667-70.4-5.589333-95.018667-28.330667-108.373334-99.712-12.245333-66.56 7.466667-125.738667 52.309334-147.242667 22.314667-10.24 74.922667-22.186667 119.765333-29.568 44.842667-5.674667 89.685333-22.186667 97.152-36.949333 7.466667-14.805333 29.866667-22.186667 52.309333-14.805333 22.314667 7.381333 52.309333 2.261333 67.242667-10.24 22.314667-19.242667 37.376-17.066667 52.309333 5.674666 14.933333 22.186667 44.842667 29.568 82.218667 22.186667z" fill="#C5161C"/></svg>
  <span class="tab-label">网易邮箱</span>
  </button>
  <button
  class="guide-tab"
  :class="{ active: activeTab === 'icloud' }"
  @click="activeTab = 'icloud'"
  >
  <svg width="16" height="16" viewBox="0 0 1024 1024"><path d="M791.488 544.095c-1.28-129.695 105.76-191.871 110.528-194.975-60.16-88.032-153.856-100.064-187.232-101.472-79.744-8.064-155.584 46.944-196.064 46.944-40.352 0-102.816-45.76-168.96-44.544-86.912 1.28-167.072 50.528-211.808 128.384-90.304 156.703-23.136 388.831 64.896 515.935 43.008 62.208 94.304 132.064 161.632 129.568 64.832-2.592 89.376-41.952 167.744-41.952s100.416 41.952 169.056 40.672c69.76-1.312 113.984-63.392 156.704-125.792 49.376-72.16 69.728-142.048 70.912-145.632-1.536-0.704-136.064-52.224-137.408-207.136zM662.56 163.52C698.304 120.16 722.432 60 715.84 0c-51.488 2.112-113.888 34.304-150.816 77.536-33.152 38.368-62.144 99.616-54.368 158.432 57.472 4.48 116.128-29.216 151.904-72.448z" fill="currentColor"/></svg>
  <span class="tab-label">iCloud邮箱</span>
  </button>
  <button
  class="guide-tab"
  :class="{ active: activeTab === 'sina' }"
  @click="activeTab = 'sina'"
  >
  <svg width="16" height="16" viewBox="0 0 1024 1024"><path d="M769.92256 503.466667c-40.96-8.618667-21.162667-30.250667-21.162667-30.250667s39.509333-66.218667-8.490666-115.2c-59.306667-60.458667-201.856 7.253333-201.856 7.253333-55.04 17.237333-39.552-7.253333-32.469334-50.432 0-50.389333-16.938667-135.381333-162.346666-84.949333-142.592 51.84-266.837333 228.949333-266.837334 228.949333C-10.792107 576.853333 0.471893 667.648 0.471893 667.648c21.162667 201.6 231.552 256.298667 393.898667 269.269333 172.202667 14.421333 402.346667-60.458667 472.917333-213.12 72.021333-151.210667-56.448-211.669333-97.408-220.330666m-361.386666 377.301333c-170.837333 7.210667-307.797333-79.232-307.797334-195.84 0-116.650667 136.96-208.810667 307.797334-217.472 169.386667-7.168 307.754667 64.853333 307.754666 180.053333 0 116.608-138.368 224.597333-307.754666 233.258667" fill="#D81E06"/><path d="M374.65856 545.237333c-170.837333 20.138667-151.04 184.32-151.04 184.32s-1.450667 51.84 46.549333 77.738667c100.266667 54.741333 203.306667 21.632 255.530667-47.488 50.816-67.712 19.754667-234.752-151.04-214.613333m-43.776 228.992c-32.469333 4.309333-57.898667-14.378667-57.898667-41.770667 0-27.306667 22.613333-56.149333 55.04-59.008 36.693333-2.901333 60.714667 18.688 60.714667 44.629333 0 27.349333-25.386667 53.290667-57.856 56.149334m100.224-87.850667c-11.306667 8.661333-23.978667 7.253333-29.653333-2.858667a25.770667 25.770667 0 0 1 7.082666-33.109333c12.672-10.112 25.386667-7.253333 31.061334 2.858667 7.04 10.069333 2.816 24.490667-8.490667 33.109333" fill="#2C2C2C"/></svg>
  <span class="tab-label">新浪邮箱</span>
  </button>
  </div>

  <!-- 教程内容区域 -->
  <div class="guide-content">
  <!-- 腾讯邮箱教程 -->
  <div v-if="activeTab === 'qq'" class="guide-panel">
  <div class="guide-step" v-for="(step, i) in qqSteps" :key="i">
  <div class="step-indicator">
  <span class="step-num">{{ i + 1 }}</span>
  <span v-if="i < qqSteps.length - 1" class="step-line"></span>
  </div>
  <div class="step-body">
  <p class="step-text">{{ step.text }}</p>
  <div v-if="step.images" class="step-images">
  <div v-for="img in step.images" :key="img.src" class="step-img-wrap" @click="previewImage(img.src)">
  <img :src="img.src" :alt="img.caption" class="step-img" />
  <span class="step-img-caption">{{ img.caption }}</span>
  </div>
  </div>
  </div>
  </div>
  <div class="guide-tip">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
  授权码只显示一次，请务必复制保存。获取授权码后，在「账号管理」中添加腾讯邮箱时填入即可。
  </div>
  </div>

  <!-- 网易邮箱教程 -->
  <div v-if="activeTab === 'netease'" class="guide-panel">
  <div class="guide-step" v-for="(step, i) in neteaseSteps" :key="i">
  <div class="step-indicator">
  <span class="step-num">{{ i + 1 }}</span>
  <span v-if="i < neteaseSteps.length - 1" class="step-line"></span>
  </div>
  <div class="step-body">
  <p class="step-text">{{ step.text }}</p>
  <div v-if="step.images" class="step-images">
  <div v-for="img in step.images" :key="img.src" class="step-img-wrap" @click="previewImage(img.src)">
  <img :src="img.src" :alt="img.caption" class="step-img" />
  <span class="step-img-caption">{{ img.caption }}</span>
  </div>
  </div>
  </div>
  </div>
  <div class="guide-tip">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
  支持 163、126、188、yeah.net 邮箱。授权码只显示一次，请务必复制保存。
  </div>
  </div>

  <!-- iCloud 邮箱教程 -->
  <div v-if="activeTab === 'icloud'" class="guide-panel">
  <div class="guide-step" v-for="(step, i) in icloudSteps" :key="i">
  <div class="step-indicator">
  <span class="step-num">{{ i + 1 }}</span>
  <span v-if="i < icloudSteps.length - 1" class="step-line"></span>
  </div>
  <div class="step-body">
  <p class="step-text" v-html="step.text"></p>
  <div v-if="step.images" class="step-images">
  <div v-for="img in step.images" :key="img.src" class="step-img-wrap" @click="previewImage(img.src)">
  <img :src="img.src" :alt="img.caption" class="step-img" />
  <span class="step-img-caption">{{ img.caption }}</span>
  </div>
  </div>
  </div>
  </div>
  <div class="guide-tip">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
  应用专用密码生成后，在「账号管理」中添加 iCloud 邮箱时填入即可。支持 @icloud.com、@me.com、@mac.com 邮箱。
  </div>
  </div>

  <!-- 新浪邮箱教程 -->
  <div v-if="activeTab === 'sina'" class="guide-panel">
  <div class="guide-step" v-for="(step, i) in sinaSteps" :key="i">
  <div class="step-indicator">
  <span class="step-num">{{ i + 1 }}</span>
  <span v-if="i < sinaSteps.length - 1" class="step-line"></span>
  </div>
  <div class="step-body">
  <p class="step-text" v-html="step.text"></p>
  <div v-if="step.images" class="step-images">
  <div v-for="img in step.images" :key="img.src" class="step-img-wrap" @click="previewImage(img.src)">
  <img :src="img.src" :alt="img.caption" class="step-img" />
  <span class="step-img-caption">{{ img.caption }}</span>
  </div>
  </div>
  </div>
  </div>
  <div class="guide-tip">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
  支持 sina.com、sina.cn、2008.sina.com、vip.sina.com、vip.sina.cn 邮箱。客户端授权码生成后，在「账号管理」中添加新浪邮箱时填入即可。
  </div>
  </div>

  </div>
  </div>
  </transition>
  </div>

  <!-- 图片预览弹窗 -->
  <transition name="fade">
  <div v-if="previewSrc" class="img-preview-overlay" @click="previewSrc = ''">
  <div class="img-preview-box" @click.stop>
  <button class="img-preview-close" @click="previewSrc = ''">
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
  </button>
  <img :src="previewSrc" class="img-preview-large" />
  </div>
  </div>
  </transition>

  <!-- 备份目录选择器（复用 NasPathPicker） -->
  <!-- 清理图床：项目内确认弹窗（非浏览器原生） -->
  <Teleport to="body">
  <transition name="fade">
  <div
  v-if="notifyPurgeConfirmVisible"
  class="notify-confirm-overlay"
  @click.self="notifyPurgeConfirmVisible = false"
  >
  <div class="notify-confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="notify-purge-title">
  <div class="notify-confirm-icon" aria-hidden="true">
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
  </svg>
  </div>
  <h3 id="notify-purge-title" class="notify-confirm-title">清理图床</h3>
  <p class="notify-confirm-message">将删除图床中的全部图片，此操作不可恢复。确定继续？</p>
  <div class="notify-confirm-actions">
  <button type="button" class="btn btn-secondary" @click="notifyPurgeConfirmVisible = false">取消</button>
  <button type="button" class="btn btn-danger" :disabled="notifyImgbedBusy" @click="confirmPurgeImgbed">确认清理</button>
  </div>
  </div>
  </div>
  </transition>
  </Teleport>

  <NasPathPicker
  v-model="showBackupPathPicker"
  mode="dir"
  title="选择备份目录"
  @confirm="onBackupPathConfirmed"
  />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import api from '../utils/api';
import { providerIcon } from '../utils/provider';
import type { BackupAccount, BackupDir } from '../types/mail';
import NasPathPicker from '../components/NasPathPicker.vue';
import { useUIStore } from '../stores/ui';

const ui = useUIStore();

// ==================== 教程数据 ====================

const activeTab = ref('qq');
const previewSrc = ref('');
const guideOpen = ref(false);
const proxyOpen = ref(false);

// 图片基础路径：Vite 构建时 base 为 /app/flymail/，需要拼接前缀才能正确访问
const guideBase = import.meta.env.BASE_URL + 'guide/';

/** 腾讯邮箱教程步骤 */
const qqSteps = [
  {
  text: '打开腾讯邮箱，点击右上角「设置」',
  images: [{ src: guideBase + 'QQ1.png', caption: '点击右上角设置' }],
  },
  {
  text: '进入设置页面，点击左侧「账号与安全」',
  images: [{ src: guideBase + 'QQ2.png', caption: '账号与安全' }],
  },
  {
  text: '选择左侧「安全设置」，开启 POP3/IMAP/SMTP/Exchange/CardDAV 服务，点击「生成授权码」，授权码只显示一次请务必复制保存',
  images: [{ src: guideBase + 'QQ3.png', caption: '开启服务并生成授权码' }],
  },
];

/** 网易邮箱教程步骤 */
const neteaseSteps = [
  {
  text: '打开网易邮箱，点击账号旁边的「设置」，选择「POP3/SMTP/IMAP」',
  images: [{ src: guideBase + 'netease1.png', caption: '进入 POP3/SMTP/IMAP 设置' }],
  },
  {
  text: '开启 POP3/SMTP/IMAP 服务，点击「生成授权码」，授权码只显示一次请务必复制保存。根据需要修改下方的收取选项',
  images: [{ src: guideBase + 'netease2.png', caption: '开启服务并生成授权码' }],
  },
];

/** iCloud 邮箱教程步骤 */
const icloudSteps = [
  {
  text: '访问 <a href="https://appleid.apple.com/account/manage" target="_blank">Apple ID 管理页面</a>，登录你的 Apple ID 账号',
  images: [{ src: guideBase + 'iCloud1.png', caption: 'Apple ID 登录页面' }],
  },
  {
  text: '在「登录与安全」部分，找到「应用专用密码」，点击「生成应用专用密码」，按提示输入标签（如 FlyMail），复制生成的密码',
  images: [{ src: guideBase + 'iCloud2.png', caption: '生成应用专用密码' }],
  },
];

/** 新浪邮箱教程步骤 */
const sinaSteps = [
  {
  text: '登录新浪邮箱网页版，点击左上角的「设置」',
  images: [{ src: guideBase + 'sina1.png', caption: '点击左上角设置' }],
  },
  {
  text: '点击左侧「客户端 POP/IMAP/SMTP」，开启 IMAP/SMTP 服务，生成客户端授权码，授权码只显示一次请务必复制保存',
  images: [{ src: guideBase + 'sina2.png', caption: '开启服务并生成授权码' }],
  },
];

function previewImage(src: string) {
  previewSrc.value = src;
}

// ==================== 设置表单逻辑 ====================

interface SettingsForm {
  gmail_proxy_enabled: boolean;
  gmail_proxy_url: string;
}

const form = ref<SettingsForm>({
  gmail_proxy_enabled: false,
  gmail_proxy_url: '',
});

const saving = ref(false);
const saveSuccess = ref(false);
const saveError = ref('');
// 代理连通性测试状态（与「关于」页检测更新交互一致）
const proxyTesting = ref(false);
const proxyTestMsg = ref('');
const proxyTestOk = ref(false);

async function loadSettingsData() {
  try {
  const data = await api.get('/settings') as any;
  form.value = {
  gmail_proxy_enabled: !!data.gmail_proxy_enabled,
  gmail_proxy_url: data.gmail_proxy_url || '',
  };
  } catch (e) {
  console.error('加载设置失败:', e);
  }
}

/** 测试当前输入框中的 HTTP 代理是否能连通 Google（无需先保存） */
async function testProxy() {
  if (proxyTesting.value) return;
  const url = form.value.gmail_proxy_url.trim();
  if (!url) {
  proxyTestOk.value = false;
  proxyTestMsg.value = '请先填写代理地址';
  return;
  }
  proxyTesting.value = true;
  proxyTestMsg.value = '';
  try {
  // 超时拉长：代理探测可能需要两次 CONNECT（IMAP + HTTPS）
  const data = await api.post('/settings/proxy/test', { proxy_url: url }, { timeout: 30000 }) as any;
  proxyTestOk.value = !!data.success;
  proxyTestMsg.value = data.message || (data.success ? '代理可用' : '代理不可用');
  } catch (e: any) {
  proxyTestOk.value = false;
  const detail = e?.response?.data?.error || e?.response?.data?.detail || e?.message;
  proxyTestMsg.value = detail ? `测试失败：${detail}` : '测试失败，请检查网络或后端服务';
  } finally {
  proxyTesting.value = false;
  }
}

// ==================== MCP 服务器设置 ====================

const mcpOpen = ref(false);
const mcpGuideTab = ref<'claude' | 'curl'>('claude');
const mcpTokenVisible = ref(false);
const mcpCopied = ref(false);
const mcpSaving = ref(false);
const mcpSuccess = ref(false);
const mcpError = ref('');

const mcpForm = ref({
  enabled: false,
  port: 9000,
  token_display: '',
  has_token: false,
  _full_token: '',
});

let mcpCopyTimer: ReturnType<typeof setTimeout> | null = null;

async function loadMcpSettings() {
  try {
  const data = await api.get('/settings/mcp') as any;
  mcpForm.value = {
  enabled: !!data.enabled,
  port: data.port || 9000,
  token_display: data.has_token ? '••••••••••••••••' : '',
  has_token: !!data.has_token,
  _full_token: '',
  };
  } catch (e) {
  console.error('加载 MCP 设置失败:', e);
  }
}

async function saveMcpSettings() {
  mcpSaving.value = true;
  mcpSuccess.value = false;
  mcpError.value = '';
  try {
  const res = await api.put('/settings/mcp', {
  enabled: mcpForm.value.enabled,
  port: mcpForm.value.port,
  }) as any;
  if (res && res.success !== false) {
  mcpSuccess.value = true;
  // 首次启用生成 token 时更新显示
  if (res.has_token && !mcpForm.value.has_token) {
  mcpForm.value.has_token = true;
  mcpForm.value.token_display = '••••••••••••••••';
  }
  await loadMcpSettings();
  setTimeout(() => { mcpSuccess.value = false; }, 3000);
  } else {
  mcpError.value = res?.message || '保存失败';
  setTimeout(() => { mcpError.value = ''; }, 5000);
  }
  } catch (e: any) {
  mcpError.value = e.message || '保存失败';
  setTimeout(() => { mcpError.value = ''; }, 5000);
  } finally {
  mcpSaving.value = false;
  }
}

async function regenerateMcpToken() {
  if (!confirm('刷新后旧令牌立即失效，已连接的 AI 助手需更新配置。确定继续？')) {
  return;
  }
  try {
  const res = await api.post('/settings/mcp/regenerate') as any;
  if (res.success) {
  mcpForm.value.has_token = true;
  mcpForm.value._full_token = res.token;
  mcpForm.value.token_display = res.token;
  mcpTokenVisible.value = true;
  // 自动复制到剪贴板
  try {
  await navigator.clipboard.writeText(res.token);
  mcpCopied.value = true;
  if (mcpCopyTimer) clearTimeout(mcpCopyTimer);
  mcpCopyTimer = setTimeout(() => { mcpCopied.value = false; }, 3000);
  } catch {
  // 剪贴板 API 可能被拒绝
  }
  }
  } catch (e: any) {
  mcpError.value = e.message || '刷新失败';
  setTimeout(() => { mcpError.value = ''; }, 5000);
  }
}

async function copyMcpToken() {
  if (!mcpForm.value.has_token) return;
  try {
  // 如果有完整 token（刚刷新过），直接用
  let token = mcpForm.value._full_token;
  if (!token) {
  // 否则提示用户先刷新令牌
  mcpError.value = '请先刷新令牌后再复制';
  setTimeout(() => { mcpError.value = ''; }, 3000);
  return;
  }
  await navigator.clipboard.writeText(token);
  mcpCopied.value = true;
  if (mcpCopyTimer) clearTimeout(mcpCopyTimer);
  mcpCopyTimer = setTimeout(() => { mcpCopied.value = false; }, 3000);
  } catch {
  mcpError.value = '复制失败，请手动复制';
  setTimeout(() => { mcpError.value = ''; }, 3000);
  }
}

onMounted(() => {
  loadSettingsData();
  loadBackupSettings();
  loadNotifySettings();
  loadMcpSettings();
  // 监听点击事件，实现下拉面板点击外部关闭
  document.addEventListener('click', handleBackupClickOutside);
});

// 组件卸载时清理监听，防止内存泄漏
onUnmounted(() => {
  document.removeEventListener('click', handleBackupClickOutside);
});

async function saveSettings() {
  saving.value = true;
  saveSuccess.value = false;
  saveError.value = '';
  try {
  const payload: Record<string, any> = {
  gmail_proxy_enabled: form.value.gmail_proxy_enabled,
  gmail_proxy_url: form.value.gmail_proxy_enabled ? form.value.gmail_proxy_url : '',
  };
  await api.put('/settings', payload);
  saveSuccess.value = true;
  await loadSettingsData();
  setTimeout(() => { saveSuccess.value = false; }, 3000);
  } catch (e: any) {
  saveError.value = e.message || '保存失败';
  setTimeout(() => { saveError.value = ''; }, 5000);
  } finally {
  saving.value = false;
  }
}

// ==================== 邮件备份设置逻辑 ====================


// ==================== 第三方通知设置 ====================

const notifyOpen = ref(false);
const notifyChannelTab = ref<'bark' | 'telegram' | 'webhook'>('bark');
const notifyBarkKeyVisible = ref(false);
const notifyTgTokenVisible = ref(false);
const notifyWhSecretVisible = ref(false);
const notifyImgbedTokenVisible = ref(false);
const notifyImgbedBusy = ref(false);
const notifyImgbedAction = ref('');
const notifyImgbedMsg = ref('');
const notifyImgbedOk = ref(false);
const notifyImgbedPreviewUrl = ref('');
const notifyPurgeConfirmVisible = ref(false);
const defaultImgbedDeployUrl = 'https://deploy.workers.cloudflare.com/?url=https://github.com/DinDing1/FlyMail/tree/main/flymail-imgbed';
const notifySaving = ref(false);
const notifySuccess = ref(false);
const notifyError = ref('');
const notifyTesting = ref(false);
const notifyTestingChannel = ref('');
const notifyTestMsg = ref('');
const notifyTestOk = ref(false);

const notifyForm = ref({
  enabled: false,
  dnd_start: '21:00',
  dnd_end: '07:00',
  mode: 'text' as 'text' | 'image',
  bark: {
    enabled: false,
    server: 'https://api.day.app',
    device_key: '',
  },
  telegram: {
    enabled: false,
    bot_token: '',
    chat_id: '',
    use_gmail_proxy: false,
  },
  webhook: {
    enabled: false,
    url: '',
    secret: '',
    use_gmail_proxy: false,
  },
  imgbed: {
    base_url: '',
    upload_token: '',
  },
  imgbed_deploy_url: defaultImgbedDeployUrl,
});




/** 加载第三方通知配置 */
async function loadNotifySettings() {
  try {
    const res = await api.get('/notify/settings') as any;
    const data = res?.data || res || {};
    notifyForm.value = {
      enabled: !!data.enabled,
      dnd_start: data.dnd_start || '21:00',
      dnd_end: data.dnd_end || '07:00',
      mode: data.mode === 'image' ? 'image' : 'text',
      bark: {
        enabled: !!(data.bark && data.bark.enabled),
        server: (data.bark && data.bark.server) || 'https://api.day.app',
        device_key: (data.bark && data.bark.device_key) || '',
      },
      telegram: {
        enabled: !!(data.telegram && data.telegram.enabled),
        bot_token: (data.telegram && data.telegram.bot_token) || '',
        chat_id: (data.telegram && data.telegram.chat_id) || '',
        use_gmail_proxy: !!(data.telegram && data.telegram.use_gmail_proxy),
      },
      webhook: {
        enabled: !!(data.webhook && data.webhook.enabled),
        url: (data.webhook && data.webhook.url) || '',
        secret: (data.webhook && data.webhook.secret) || '',
        use_gmail_proxy: !!(data.webhook && data.webhook.use_gmail_proxy),
      },
      imgbed: {
        base_url: (data.imgbed && data.imgbed.base_url) || '',
        upload_token: (data.imgbed && data.imgbed.upload_token) || '',
      },
      imgbed_deploy_url: data.imgbed_deploy_url || defaultImgbedDeployUrl,
    };
  } catch (e) {
    console.error('加载通知设置失败:', e);
  }
}

/** 保存第三方通知配置 */
async function saveNotifySettings() {
  notifySaving.value = true;
  notifySuccess.value = false;
  notifyError.value = '';
  try {
    const res = await api.put('/notify/settings', {
      enabled: notifyForm.value.enabled,
      dnd_start: notifyForm.value.dnd_start,
      dnd_end: notifyForm.value.dnd_end,
      mode: notifyForm.value.mode,
      bark: { ...notifyForm.value.bark },
      telegram: { ...notifyForm.value.telegram },
      webhook: { ...notifyForm.value.webhook },
      imgbed: { ...notifyForm.value.imgbed },
    }) as any;
    if (res && res.success === false) {
      notifyError.value = res.message || '保存失败';
      setTimeout(() => { notifyError.value = ''; }, 5000);
      return;
    }
    notifySuccess.value = true;
    await loadNotifySettings();
    setTimeout(() => { notifySuccess.value = false; }, 2500);
  } catch (e: any) {
    notifyError.value = e.message || '保存失败';
    setTimeout(() => { notifyError.value = ''; }, 5000);
  } finally {
    notifySaving.value = false;
  }
}

/** 测试指定渠道（绕过总开关与免打扰） */
async function testNotifyChannel(channel: 'bark' | 'telegram' | 'webhook') {
  if (notifyTesting.value) return;
  notifyTesting.value = true;
  notifyTestingChannel.value = channel;
  notifyTestMsg.value = '';
  notifyTestOk.value = false;
  try {
    // 先保存当前表单，避免测试的是旧配置
    await api.put('/notify/settings', {
      enabled: notifyForm.value.enabled,
      dnd_start: notifyForm.value.dnd_start,
      dnd_end: notifyForm.value.dnd_end,
      mode: notifyForm.value.mode,
      bark: { ...notifyForm.value.bark },
      telegram: { ...notifyForm.value.telegram },
      webhook: { ...notifyForm.value.webhook },
      imgbed: { ...notifyForm.value.imgbed },
    });
    // 图片模式需生成卡片 + 图床上传，超时放宽
    const testTimeout = notifyForm.value.mode === 'image' ? 60000 : 30000;
    const res = await api.post('/notify/test', { channel }, { timeout: testTimeout }) as any;
    notifyTestOk.value = !!res?.success;
    notifyTestMsg.value = res?.message || (res?.success ? '测试成功' : '测试失败');
  } catch (e: any) {
    notifyTestOk.value = false;
    const detail = e?.response?.data?.message || e?.response?.data?.detail || e?.message;
    notifyTestMsg.value = detail ? `测试失败：${detail}` : '测试失败';
  } finally {
    notifyTesting.value = false;
  }
}

/** 组装图床配置载荷（测试时带上未保存表单） */
function imgbedPayload() {
  return {
    imgbed: {
      base_url: notifyForm.value.imgbed.base_url,
      upload_token: notifyForm.value.imgbed.upload_token,
    },
  };
}

/** 测试自建图床：探活 + 上传测试卡片 */
async function testImgbed() {
  if (notifyImgbedBusy.value) return;
  notifyImgbedBusy.value = true;
  notifyImgbedAction.value = 'test';
  notifyImgbedMsg.value = '';
  notifyImgbedOk.value = false;
  notifyImgbedPreviewUrl.value = '';
  try {
    const res = await api.post('/notify/imgbed/test', imgbedPayload(), { timeout: 45000 }) as any;
    notifyImgbedOk.value = !!res?.success;
    notifyImgbedMsg.value = res?.message || (res?.success ? '测试成功' : '测试失败');
    if (res?.success && res?.data?.url) {
      notifyImgbedPreviewUrl.value = res.data.url;
      // 测试成功后自动落库图床配置，便于 Bark 图片推送立刻可用
      try {
        await api.put('/notify/settings', {
          enabled: notifyForm.value.enabled,
          dnd_start: notifyForm.value.dnd_start,
          dnd_end: notifyForm.value.dnd_end,
          mode: notifyForm.value.mode,
          bark: { ...notifyForm.value.bark },
          telegram: { ...notifyForm.value.telegram },
          webhook: { ...notifyForm.value.webhook },
          imgbed: { ...notifyForm.value.imgbed },
        });
      } catch {
        /* 自动保存失败不阻断测试结果展示 */
      }
    }
  } catch (e: any) {
    notifyImgbedOk.value = false;
    const detail = e?.response?.data?.message || e?.response?.data?.detail || e?.message;
    notifyImgbedMsg.value = detail ? `测试失败：${detail}` : '测试失败';
  } finally {
    notifyImgbedBusy.value = false;
    notifyImgbedAction.value = '';
  }
}

/** 打开清理图床确认弹窗（项目内样式，非 window.confirm） */
function purgeImgbed() {
  if (notifyImgbedBusy.value) return;
  notifyPurgeConfirmVisible.value = true;
}

/** 确认后执行图床清理 */
async function confirmPurgeImgbed() {
  if (notifyImgbedBusy.value) return;
  notifyPurgeConfirmVisible.value = false;

  notifyImgbedBusy.value = true;
  notifyImgbedAction.value = 'purge';
  notifyImgbedMsg.value = '';
  notifyImgbedOk.value = false;
  notifyImgbedPreviewUrl.value = '';
  try {
    const res = await api.post('/notify/imgbed/purge', imgbedPayload(), { timeout: 60000 }) as any;
    notifyImgbedOk.value = !!res?.success;
    notifyImgbedMsg.value = res?.message || (res?.success ? '清理完成' : '清理失败');
    if (res?.success) {
      ui.success(notifyImgbedMsg.value || '清理完成');
    } else {
      ui.error(notifyImgbedMsg.value || '清理失败');
    }
  } catch (e: any) {
    notifyImgbedOk.value = false;
    const detail = e?.response?.data?.message || e?.response?.data?.detail || e?.message;
    notifyImgbedMsg.value = detail ? `清理失败：${detail}` : '清理失败';
    ui.error(notifyImgbedMsg.value);
  } finally {
    notifyImgbedBusy.value = false;
    notifyImgbedAction.value = '';
  }
}


const backupOpen = ref(false);
const backupSaving = ref(false);
const backupSuccess = ref(false);
const backupError = ref('');
const backupAccounts = ref<BackupAccount[]>([]);
const backupAvailableDirs = ref<BackupDir[]>([]);
// 下拉多选状态
const backupDropdownOpen = ref(false);
const backupSelectRef = ref<HTMLElement | null>(null);

// 目录选择器状态（NasPathPicker 控制显示）
const showBackupPathPicker = ref(false);
const backupAccessiblePaths = ref<string[]>([]);

interface BackupForm {
  enabled: boolean;
  account_ids: string[];
  target_dir: string;
}

const backupForm = ref<BackupForm>({
  enabled: false,
  account_ids: [],
  target_dir: '',
});

/** 加载备份配置 */
async function loadBackupSettings() {
  try {
  const data = await api.get('/backup/settings') as any;
  backupAccounts.value = data.accounts || [];
  backupAvailableDirs.value = data.available_dirs || [];
  backupForm.value = {
  enabled: !!data.enabled,
  account_ids: [...(data.account_ids || [])],
  target_dir: data.target_dir || '',
  };
  } catch (e) {
  console.error('加载备份设置失败:', e);
  }
}

/** 切换账号选中状态 */
function toggleBackupAccount(accountId: string) {
  const idx = backupForm.value.account_ids.indexOf(accountId);
  if (idx === -1) {
  backupForm.value.account_ids.push(accountId);
  } else {
  backupForm.value.account_ids.splice(idx, 1);
  }
}

/** 根据账号 ID 获取邮箱地址（用于标签显示） */
function getAccountEmail(accountId: string): string {
  const acc = backupAccounts.value.find(a => a.id === accountId);
  return acc?.email || accountId;
}

/** 根据账号 ID 获取邮箱提供商（用于标签图标） */
function getAccountProvider(accountId: string): string {
  const acc = backupAccounts.value.find(a => a.id === accountId);
  return acc?.provider || '';
}

/** 点击外部关闭下拉面板 */
function handleBackupClickOutside(e: MouseEvent) {
  if (backupSelectRef.value && !backupSelectRef.value.contains(e.target as Node)) {
  backupDropdownOpen.value = false;
  }
}

/** 保存备份配置 */
async function saveBackupSettings() {
  backupSaving.value = true;
  backupSuccess.value = false;
  backupError.value = '';
  try {
  const res = await api.put('/backup/settings', {
  enabled: backupForm.value.enabled,
  account_ids: backupForm.value.account_ids,
  target_dir: backupForm.value.target_dir,
  }) as any;
  // 后端可能返回 success=false（如 target_dir 不在授权目录内）
  if (res && res.success === false) {
  backupError.value = res.message || '保存失败';
  setTimeout(() => { backupError.value = ''; }, 5000);
  return;
  }
  backupSuccess.value = true;
  await loadBackupSettings();
  setTimeout(() => { backupSuccess.value = false; }, 2500);
  } catch (e: any) {
  backupError.value = e.message || '保存失败';
  setTimeout(() => { backupError.value = ''; }, 5000);
  } finally {
  backupSaving.value = false;
  }
}

// ==================== 备份目录选择器（NasPathPicker） ====================

/** 加载飞牛授权目录列表（刷新按钮用） */
async function loadBackupAccessiblePaths() {
  try {
  const data = await api.get('/backup/accessible-paths') as any;
  backupAccessiblePaths.value = data.paths || [];
  } catch (e) {
  console.error('加载授权目录失败:', e);
  backupAccessiblePaths.value = [];
  }
}

/** 打开目录选择器弹窗 */
function openBackupPathPicker() {
  if (!backupForm.value.enabled) return;
  showBackupPathPicker.value = true;
}

/** 确认选择，将当前路径写回复份配置 */
function onBackupPathConfirmed(path: string) {
  backupForm.value.target_dir = path;
  showBackupPathPicker.value = false;
}
</script>

<style scoped>
.settings-page {
  /* 覆盖 App.vue .content>* 的 display:flex，避免展开后卡片被 flex 压缩裁剪 */
  display: block;
  flex: 1;
  min-height: 0;
  height: 100%;
  overflow-x: hidden;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding: var(--space-6);
  background: var(--bg-secondary);
  box-sizing: border-box;
}

/* Gmail 代理配置卡片 */
.provider-card {
  background: var(--bg-card);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-card);
  overflow: hidden;
  margin-bottom: var(--space-4);
  /* 禁止在父级 flex 场景下被压扁，保证展开内容完整可见 */
  flex-shrink: 0;
}

.gmail-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-5);
  border: none;
  background: linear-gradient(135deg, #FFF5F5 0%, #FFF0F0 100%);
  cursor: pointer;
  font-family: inherit;
  transition: background var(--transition-fast);
}

.gmail-toggle:hover {
  background: linear-gradient(135deg, #FFECEC 0%, #FFE5E5 100%);
}

.gmail-toggle-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.gmail-toggle-icon {
  width: 36px;
  height: 36px;
  border-radius: 9px;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(234, 67, 53, 0.1);
  flex-shrink: 0;
}

.gmail-toggle-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
  text-align: left;
}

.gmail-toggle-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.gmail-toggle-desc {
  font-size: 11px;
  color: var(--text-tertiary);
}


/* 通知设置卡片：紫靛渐变，区别备份蓝 / Gmail 红 */
.notify-toggle {
  background: linear-gradient(135deg, #F5F0FF 0%, #EFE8FF 100%);
}
.notify-toggle:hover {
  background: linear-gradient(135deg, #EDE5FF 0%, #E6DCFF 100%);
}
.notify-toggle-icon {
  background: white;
  box-shadow: 0 2px 8px rgba(88, 86, 214, 0.14);
  color: #5856D6;
}
.notify-dim {
  /* 仅弱化，不隐藏结构；交互由 disabled 控制 */
  opacity: 0.72;
  pointer-events: none;
}
/* 免打扰 | 通知模式 左右并排 */
.notify-inline-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px 16px;
  align-items: start;
  margin-bottom: var(--space-3);
}
.notify-inline-field {
  margin-bottom: 0 !important;
  min-width: 0;
}
.notify-inline-field .field-label {
  margin-bottom: 8px;
}
.notify-inline-field .field-hint {
  margin-top: 6px;
  line-height: 1.35;
  font-size: 11px;
}
.notify-dnd-row {
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: 100%;
  min-height: 36px;
}
.notify-time {
  flex: 1;
  min-width: 0;
  max-width: none;
  height: 36px;
  box-sizing: border-box;
}
.notify-dnd-sep {
  color: var(--text-secondary);
  font-size: var(--text-sm);
  flex-shrink: 0;
}
/* 分段控件（紧凑，对齐时间输入高度） */
.notify-segment {
  display: flex;
  width: 100%;
  max-width: none;
  height: 36px;
  padding: 3px;
  box-sizing: border-box;
  border-radius: 9px;
  background: rgba(0, 0, 0, 0.06);
  border: 1px solid var(--border-color);
  gap: 2px;
}
.notify-segment-item {
  flex: 1;
  min-width: 0;
  height: 100%;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.15s ease;
  line-height: 1;
}
.notify-segment-item:hover:not(:disabled):not(.active) {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.45);
}
.notify-segment-item.active {
  background: var(--bg-card, #fff);
  color: var(--text-primary);
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}
.notify-segment-item:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}
.notify-inline-mode {
  display: flex;
  flex-direction: column;
}
.notify-inline-dnd .notify-dnd-row,
.notify-inline-mode .notify-segment {
  width: 100%;
  align-self: stretch;
}
.notify-channels {
  margin-top: var(--space-3);
  margin-bottom: var(--space-3);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
  background: var(--bg-secondary, #f5f5f7);
}
.notify-guide-tabs {
  border-radius: 0;
  margin: 0;
  padding: 4px !important;
  background: rgba(0, 0, 0, 0.04);
  border-bottom: none;
  gap: 4px;
}
.notify-guide-tabs .guide-tab {
  flex: 1;
  justify-content: center;
  padding: 8px 12px;
}
.notify-guide-tabs .guide-tab:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.notify-channel-panel {
  padding: var(--space-3) var(--space-4);
  background: var(--bg-card);
}
.notify-secret-row {
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: 520px;
}
.notify-secret-row .input {
  flex: 1;
}
.btn-secret-toggle {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.btn-secret-toggle:hover {
  color: var(--text-primary);
  background: var(--bg-tertiary);
}
.notify-test-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 4px;
}
.notify-warn-hint {
  color: #B25000 !important;
}
.notify-tip {
  margin-top: var(--space-3);
}

/* 清理图床确认弹窗 */
.notify-confirm-overlay {
  position: fixed;
  inset: 0;
  z-index: 5000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.42);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}
.notify-confirm-dialog {
  width: min(400px, 100%);
  padding: 22px 22px 18px;
  border-radius: 14px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, rgba(0,0,0,0.08));
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.22);
  text-align: center;
  animation: notifyConfirmIn 0.18s ease;
}
@keyframes notifyConfirmIn {
  from { opacity: 0; transform: translateY(8px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.notify-confirm-icon {
  width: 44px;
  height: 44px;
  margin: 0 auto 12px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ff3b30;
  background: rgba(255, 59, 48, 0.1);
}
.notify-confirm-title {
  margin: 0 0 8px;
  font-size: 17px;
  font-weight: 650;
  color: var(--text-primary, #1d1d1f);
}
.notify-confirm-message {
  margin: 0 0 18px;
  font-size: 13px;
  line-height: 1.55;
  color: var(--text-secondary, #6e6e73);
}
.notify-confirm-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
}
.notify-confirm-actions .btn {
  min-width: 96px;
}
.notify-confirm-actions .btn-danger {
  background: #ff3b30;
  border-color: #ff3b30;
  color: #fff;
}
.notify-confirm-actions .btn-danger:hover {
  filter: brightness(0.96);
}
.notify-confirm-actions .btn-danger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 全局 Cloudflare 图床（免打扰行下方；多渠道共用） */
.notify-imgbed {
  margin-top: 12px;
  padding: 12px 14px;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(88, 86, 214, 0.04) 0%, rgba(0, 122, 255, 0.03) 100%);
}
.notify-imgbed-head {
  margin-bottom: 10px;
}
.notify-imgbed-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 4px;
}
.notify-imgbed-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}
.notify-imgbed-desc {
  display: block;
  margin-top: 0 !important;
  line-height: 1.4;
}
.notify-imgbed-fields {
  margin-bottom: 8px !important;
}
.notify-imgbed-fields .field {
  margin-bottom: 0 !important;
}
.notify-secret-row-full {
  max-width: none;
  width: 100%;
}
/* Deploy to Cloudflare — 官方深色徽章风格 */
.cf-deploy-btn {
  --cf-orange: #F6821F;
  text-decoration: none !important;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-shrink: 0;
  height: 32px;
  padding: 0 14px 0 12px;
  border-radius: 999px;
  background: #111827;
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow:
    0 1px 2px rgba(0, 0, 0, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
  transition: background 0.15s ease, box-shadow 0.15s ease, transform 0.12s ease;
  line-height: 1;
  white-space: nowrap;
  user-select: none;
}
.cf-deploy-btn:hover {
  background: #1f2937;
  box-shadow:
    0 2px 8px rgba(0, 0, 0, 0.22),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
  color: #fff !important;
}
.cf-deploy-btn:active {
  transform: translateY(1px);
  background: #0b1220;
}
.cf-deploy-cloud {
  width: 18px;
  height: 12px;
  flex-shrink: 0;
  display: block;
}
.cf-deploy-text {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: #f5f5f7;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}
.notify-toggle-pair {
  margin-bottom: 8px !important;
  align-items: center;
}
.notify-toggle-pair .proxy-field {
  margin-bottom: 0 !important;
}
.notify-toggle-pair .proxy-label {
  margin-bottom: 0;
}
.notify-warn-hint {
  display: block;
  margin: -2px 0 10px;
  color: #c77a00;
}

.notify-purge-btn {
  opacity: 0.92;
}
.notify-imgbed-link {
  margin-left: 8px;
  color: var(--accent-blue, #007AFF);
  text-decoration: underline;
  font-size: 12px;
}
.notify-imgbed .notify-test-row {
  margin-top: 2px;
}

/* 备份卡片头部：使用蓝色渐变区别于 Gmail 代理的红色 */
.backup-toggle {
  background: linear-gradient(135deg, #F0F7FF 0%, #EBF3FF 100%);
}

.backup-toggle:hover {
  background: linear-gradient(135deg, #E5F0FF 0%, #DDEBFF 100%);
}

.backup-toggle-icon {
  background: white;
  box-shadow: 0 2px 8px rgba(0, 122, 255, 0.12);
  color: var(--accent-blue, #007AFF);
}

/* 备份邮箱下拉多选 */
.backup-multi-select {
  position: relative;
  max-width: 520px;
}

.backup-multi-select.disabled {
  opacity: 0.5;
  pointer-events: none;
}

/* 触发器：显示已选标签或占位文字 */
.select-trigger {
  min-height: 38px;
  padding: 6px 32px 6px 8px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--bg-card);
  cursor: pointer;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  transition: border-color 0.15s, box-shadow 0.15s;
  position: relative;
}

.select-trigger:hover {
  border-color: rgba(0, 0, 0, 0.2);
}

.select-trigger:focus-within {
  border-color: var(--accent-blue, #007AFF);
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.1);
}

/* 已选邮箱标签容器 */
.selected-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  width: 100%;
}

/* 单个已选标签 */
.selected-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 4px 3px 8px;
  background: rgba(0, 122, 255, 0.1);
  border-radius: 6px;
  font-size: 12px;
  color: var(--accent-blue, #007AFF);
  max-width: 200px;
}

.tag-icon {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.tag-icon svg {
  width: 14px;
  height: 14px;
}

.tag-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tag-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border: none;
  background: transparent;
  border-radius: 50%;
  cursor: pointer;
  color: var(--accent-blue, #007AFF);
  opacity: 0.6;
  flex-shrink: 0;
  padding: 0;
  transition: opacity 0.15s, background 0.15s;
}

.tag-remove:hover {
  opacity: 1;
  background: rgba(0, 122, 255, 0.15);
}

/* 占位文字 */
.select-placeholder {
  color: var(--text-tertiary, #8E8E93);
  font-size: var(--text-sm);
  padding: 2px 4px;
}

/* 下拉箭头 */
.select-arrow {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-tertiary, #8E8E93);
  transition: transform 0.2s ease;
  pointer-events: none;
}

.select-arrow.open {
  transform: translateY(-50%) rotate(180deg);
}

/* 下拉面板 */
.select-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  max-height: 240px;
  overflow-y: auto;
  z-index: 100;
  padding: 4px;
}

/* 下拉项 */
.dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--text-primary);
  transition: background 0.12s;
}

.dropdown-item:hover {
  background: var(--bg-hover);
}

.dropdown-item.checked {
  background: rgba(0, 122, 255, 0.06);
}

.dropdown-item input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: var(--accent-blue, #007AFF);
  flex-shrink: 0;
}

.dropdown-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.dropdown-email {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 下拉展开/收起动画 */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* 备份位置行（路径显示 + 浏览按钮 + 刷新按钮） */
.backup-path-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.backup-path-display {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--bg-card);
  cursor: pointer;
  transition: border-color 0.2s;
}

.backup-path-display:hover {
  border-color: var(--accent-blue, #007AFF);
}

.backup-path-text {
  font-size: var(--text-sm);
  color: var(--text-primary);
  word-break: break-all;
  flex: 1;
  margin-right: 8px;
}

.backup-path-text.path-empty {
  color: var(--text-tertiary);
}

.btn-browse {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-browse:hover:not(:disabled) {
  background: var(--bg-tertiary);
  color: var(--accent-blue, #007AFF);
}

.btn-browse:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-browse svg {
  width: 16px;
  height: 16px;
}

.btn-refresh-paths {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-refresh-paths:hover {
  border-color: var(--accent-blue, #007AFF);
  color: var(--accent-blue, #007AFF);
}

.btn-refresh-paths svg {
  width: 14px;
  height: 14px;
}

/* ==================== 目录选择器弹窗 ==================== */
.glass-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(8px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.backup-path-picker.modal {
  width: 90%;
  max-width: 560px;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  border-radius: 16px;
  overflow: hidden;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.modal-head h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.btn-icon-sm {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-icon-sm:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.btn-icon-sm svg {
  width: 16px;
  height: 16px;
}

.modal-nav {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 2px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border-color);
  font-size: 13px;
}

.nav-item {
  color: var(--accent-blue, #007AFF);
  cursor: pointer;
  transition: opacity 0.2s;
}

.nav-item:hover {
  opacity: 0.7;
}

.nav-sep {
  margin: 0 4px;
  color: var(--text-tertiary);
}

.modal-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.modal-empty {
  padding: 40px 20px;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 13px;
  line-height: 1.6;
}

.modal-dir {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 20px;
  cursor: pointer;
  transition: background 0.15s;
}

.modal-dir:hover {
  background: var(--bg-hover);
}

.modal-dir svg {
  width: 18px;
  height: 18px;
  color: var(--accent-blue, #007AFF);
  flex-shrink: 0;
}

.modal-dir span {
  font-size: 13px;
  color: var(--text-primary);
  word-break: break-all;
}

.modal-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  border-top: 1px solid var(--border-color);
  gap: 12px;
}

.modal-path {
  flex: 1;
  font-size: 12px;
  color: var(--text-secondary);
  word-break: break-all;
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
}

.modal-btns {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.card-body {
  padding: var(--space-6);
}

.field {
  margin-bottom: var(--space-5);
}

.field:last-of-type {
  margin-bottom: 0;
}

.field-label {
  display: block;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--space-2);
}

.field-input {
  position: relative;
  max-width: 520px;
}

/* 代理地址 + 测试按钮同一行 */
.proxy-url-row {
  display: flex;
  align-items: center;
  gap: 10px;
  max-width: 640px;
}

.proxy-url-row .input {
  flex: 1;
  min-width: 0;
}

/* 对齐「关于」页 .check-update-btn：圆角描边、悬停变强调色 */
.check-proxy-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius-full, 20px);
  background: var(--bg-hover);
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: all 0.15s ease;
}

.check-proxy-btn:hover:not(:disabled) {
  background: var(--color-accent);
  color: #fff;
  border-color: var(--color-accent);
}

.check-proxy-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spin-icon {
  animation: proxy-spin 0.8s linear infinite;
}

@keyframes proxy-spin {
  to { transform: rotate(360deg); }
}

.field-hint {
  display: block;
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  margin-top: 6px;
  line-height: 1.4;
}

.proxy-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: 500;
}

.toggle-switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 22px;
  flex-shrink: 0;
  cursor: pointer;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  inset: 0;
  background: var(--bg-tertiary);
  border-radius: 22px;
  transition: background 0.2s;
}

.toggle-slider::before {
  content: '';
  position: absolute;
  width: 18px;
  height: 18px;
  left: 2px;
  top: 2px;
  background: #fff;
  border-radius: 50%;
  transition: transform 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.toggle-switch input:checked + .toggle-slider {
  background: var(--color-accent);
}

.toggle-switch input:checked + .toggle-slider::before {
  transform: translateX(18px);
}

.save-bar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-6);
  padding-top: var(--space-5);
  border-top: 1px solid var(--border-color);
}

.btn-save {
  min-width: 120px;
}

.saving-text {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.saving-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse 1s infinite;
}

.status-msg {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: var(--text-sm);
  font-weight: 500;
}

.status-msg.success { color: var(--color-success); }
.status-msg.error { color: var(--color-danger); }

/* ==================== 配置教程样式 ==================== */

.guide-section {
  background: var(--bg-card);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-card);
  overflow: hidden;
  flex-shrink: 0;
  margin-bottom: var(--space-4);
}

/* 折叠按钮 */
.guide-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-5);
  border: none;
  background: transparent;
  cursor: pointer;
  font-family: inherit;
  transition: background var(--transition-fast);
}

.guide-toggle:hover {
  background: var(--bg-hover);
}

.guide-toggle-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.guide-toggle-icon {
  width: 36px;
  height: 36px;
  border-radius: 9px;
  background: linear-gradient(135deg, #EBF5FF 0%, #E8F0FE 100%);
  color: #4285F4;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.guide-toggle-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
  text-align: left;
}

.guide-toggle-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.guide-toggle-desc {
  font-size: 11px;
  color: var(--text-tertiary);
}

.guide-arrow {
  color: var(--text-tertiary);
  transition: transform var(--transition-normal);
  flex-shrink: 0;
}

.guide-arrow.open {
  transform: rotate(180deg);
}

/* 折叠内容 */
.guide-body {
  border-top: 1px solid var(--border-color);
}

/* Tab 切换 */
.guide-tabs {
  display: flex;
  gap: 2px;
  padding: var(--space-2) var(--space-6);
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-color);
}

.guide-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: none;
  background: transparent;
  border-radius: 8px;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.guide-tab:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.guide-tab.active {
  background: var(--bg-card);
  color: var(--text-primary);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

/* 教程内容 */
.guide-content {
  padding: var(--space-6);
}

.guide-panel {
  animation: fadeIn 0.25s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 步骤条 */
.guide-step {
  display: flex;
  gap: var(--space-4);
  position: relative;
}

.guide-step:not(:last-child) {
  padding-bottom: var(--space-5);
}

.step-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
  width: 28px;
}

.step-num {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--color-accent);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
  z-index: 1;
}

.step-line {
  width: 2px;
  flex: 1;
  background: var(--border-color);
  margin-top: 6px;
  border-radius: 1px;
}

.guide-step:last-child .step-num {
  background: var(--color-success);
}

.step-body {
  flex: 1;
  min-width: 0;
  padding-top: 3px;
}

.step-text {
  font-size: var(--text-sm);
  color: var(--text-primary);
  line-height: 1.7;
  margin-bottom: var(--space-3);
}

.step-text :deep(a) {
  color: var(--color-accent);
  text-decoration: none;
  font-weight: 500;
}

.step-text :deep(a:hover) {
  text-decoration: underline;
}

/* 步骤文本中的代码片段（IP、域名、URL 等） */
.step-text :deep(code) {
  font-family: 'SF Mono', ' Monaco', 'Consolas', monospace;
  font-size: 0.9em;
  padding: 1px 6px;
  background: var(--bg-tertiary);
  border-radius: 4px;
  color: var(--color-accent);
  word-break: break-all;
}

.step-text :deep(strong) {
  font-weight: 600;
  color: var(--text-primary);
}

/* 步骤截图 */
.step-images {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.step-img-wrap {
  cursor: pointer;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid var(--border-color);
  transition: all 0.2s ease;
  background: var(--bg-tertiary);
}

.step-img-wrap:hover {
  border-color: var(--color-accent);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.step-img {
  display: block;
  max-width: 320px;
  max-height: 220px;
  object-fit: contain;
  background: white;
}

.step-img-caption {
  display: block;
  padding: 6px 10px;
  font-size: 11px;
  color: var(--text-tertiary);
  text-align: center;
  background: var(--bg-card);
}

/* 提示框 */
.guide-tip {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  margin-top: var(--space-5);
  padding: var(--space-3) var(--space-4);
  background: #FFF8E1;
  border-radius: 8px;
  font-size: var(--text-xs);
  color: #795500;
  line-height: 1.6;
  border: 1px solid #FFE082;
}

.guide-tip svg {
  flex-shrink: 0;
  margin-top: 2px;
  color: #F9A825;
}

/* ==================== 图片预览弹窗 ==================== */

.img-preview-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(4px);
}

.img-preview-box {
  position: relative;
  max-width: 90vw;
  max-height: 90vh;
}

.img-preview-close {
  position: absolute;
  top: -12px;
  right: -12px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: white;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  color: var(--text-secondary);
  transition: all 0.15s ease;
}

.img-preview-close:hover {
  background: var(--color-danger);
  color: white;
}

.img-preview-large {
  max-width: 90vw;
  max-height: 90vh;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

/* 动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 展开动画：仅淡入位移，不用 max-height，避免高内容被裁切 */
.expand-enter-active,
.expand-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.expand-enter-to,
.expand-leave-from {
  opacity: 1;
  transform: translateY(0);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* 移动端适配 */
@media (max-width: 768px) {
  .notify-inline-row {
  grid-template-columns: 1fr;
  gap: 14px;
  }

  .settings-page {
  padding: var(--space-4);
  }

  .card-body {
  padding: var(--space-4);
  }

  .save-bar {
  flex-wrap: wrap;
  }

  .btn-save {
  width: 100%;
  justify-content: center;
  }

  .guide-tabs {
  padding: var(--space-2);
  gap: 4px;
  }

  .guide-tab {
  flex: 1;
  justify-content: center;
  padding: 10px 6px;
  font-size: 13px;
  }

  /* 移动端平台 Tab 只显示图标，隐藏文字 */
  .guide-tab svg {
  width: 20px;
  height: 20px;
  }

  .guide-tab .tab-label {
  display: none;
  }

  .guide-content {
  padding: var(--space-4);
  }

  .step-img {
  max-width: 100%;
  }

  .step-images {
  flex-direction: column;
  }
}

.btn-save {
  align-self: flex-start;
  padding: 8px 20px;
  border: none;
  border-radius: 6px;
  background: var(--accent-blue, #007AFF);
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: opacity 0.15s;
}

.btn-save:hover { opacity: 0.9; }
.btn-save:disabled { opacity: 0.5; cursor: not-allowed; }

.empty-hint {
  color: var(--text-tertiary);
  font-size: 14px;
  text-align: center;
  padding: 20px 0;
}

/* ==================== MCP 服务器设置样式 ==================== */

.mcp-config-code {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 12px;
  padding: 12px 16px;
  background: var(--bg-tertiary);
  border-radius: 8px;
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.6;
  color: var(--text-primary);
  overflow-x: auto;
}

.mcp-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 12px;
}

.mcp-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.mcp-status-dot.status-ok {
  background: var(--color-success, #34C759);
  box-shadow: 0 0 4px var(--color-success, #34C759);
}

.mcp-status-dot.status-off {
  background: var(--text-tertiary);
}

/* 复用现有 btn-secret-toggle 样式，确保对齐 */
.btn-secret-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius-full, 20px);
  background: var(--bg-hover);
  color: var(--text-secondary);
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.15s ease;
}

.btn-secret-toggle:hover:not(:disabled) {
  background: var(--bg-card);
  color: var(--text-primary);
}

.btn-secret-toggle:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
