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

  <!-- 备份目录选择器弹窗 -->
  <div v-if="showBackupPathPicker" class="glass-overlay" @click.self="showBackupPathPicker = false">
  <div class="modal backup-path-picker">
  <div class="modal-head">
  <h4>选择备份目录</h4>
  <button class="btn-icon-sm neu-circle" @click="showBackupPathPicker = false">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
  </button>
  </div>
  <div class="modal-nav">
  <span v-if="backupPickerBreadcrumbs.length === 0" class="nav-item">授权目录</span>
  <template v-for="(b, i) in backupPickerBreadcrumbs" :key="i">
  <span class="nav-item" @click="backupPickerNavigateTo(i)">
  {{ b.name }}<span v-if="i < backupPickerBreadcrumbs.length - 1" class="nav-sep">/</span>
  </span>
  </template>
  </div>
  <div class="modal-list">
  <div v-if="backupPickerLoading" class="modal-empty">加载中...</div>
  <div v-else-if="backupPickerDirs.length === 0" class="modal-empty">
  {{ backupPickerBreadcrumbs.length === 0 ? '暂无可用授权目录，请先在飞牛应用设置中授权目录后点击"刷新"' : '此目录下无子目录' }}
  </div>
  <div v-else v-for="dir in backupPickerDirs" :key="dir" class="modal-dir" @click="backupPickerEnterDir(dir)">
  <svg viewBox="0 0 24 24" fill="currentColor"><path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>
  <span>{{ pathBasename(dir) }}</span>
  </div>
  </div>
  <div class="modal-foot">
  <span class="modal-path">{{ backupPickerCurrentPath || '请选择目录' }}</span>
  <div class="modal-btns">
  <button class="btn-save" @click="confirmBackupPathPick" :disabled="!backupPickerCurrentPath">确定</button>
  </div>
  </div>
  </div>
  </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import api from '../utils/api';
import { providerIcon } from '../utils/provider';
import type { BackupAccount, BackupDir } from '../types/mail';

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

onMounted(() => {
  loadSettingsData();
  loadBackupSettings();
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

const backupOpen = ref(false);
const backupSaving = ref(false);
const backupSuccess = ref(false);
const backupError = ref('');
const backupAccounts = ref<BackupAccount[]>([]);
const backupAvailableDirs = ref<BackupDir[]>([]);
// 下拉多选状态
const backupDropdownOpen = ref(false);
const backupSelectRef = ref<HTMLElement | null>(null);

// 目录选择器状态（面包屑导航 + 逐级浏览）
const showBackupPathPicker = ref(false);
const backupPickerLoading = ref(false);
const backupPickerDirs = ref<string[]>([]);
const backupPickerBreadcrumbs = ref<{ name: string; path: string }[]>([]);
const backupPickerCurrentPath = ref('');
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

// ==================== 备份目录选择器（面包屑+逐级浏览） ====================

/** 获取路径的 basename（最后一级目录名） */
function pathBasename(path: string): string {
  const parts = path.replace(/\\/g, '/').split('/').filter(Boolean);
  return parts[parts.length - 1] || path;
}

/** 加载飞牛授权目录列表（供目录选择器初始展示） */
async function loadBackupAccessiblePaths() {
  try {
  const data = await api.get('/backup/accessible-paths') as any;
  backupAccessiblePaths.value = data.paths || [];
  // 如果选择器已打开，更新列表
  if (showBackupPathPicker.value && backupPickerBreadcrumbs.value.length === 0) {
  backupPickerDirs.value = backupAccessiblePaths.value;
  }
  } catch (e) {
  console.error('加载授权目录失败:', e);
  backupAccessiblePaths.value = [];
  }
}

/** 打开目录选择器弹窗 */
function openBackupPathPicker() {
  backupPickerBreadcrumbs.value = [];
  backupPickerCurrentPath.value = '';
  backupPickerDirs.value = backupAccessiblePaths.value;
  showBackupPathPicker.value = true;
  // 首次打开时自动加载授权目录
  if (backupAccessiblePaths.value.length === 0) {
  loadBackupAccessiblePaths();
  }
}

/** 进入下一层目录
 *  点击授权目录（顶层）时重置面包屑，点击子目录时追加到面包屑
 */
async function backupPickerEnterDir(dir: string) {
  const dirName = pathBasename(dir);
  // 点击的是授权目录（顶层）→ 重置面包屑
  if (backupAccessiblePaths.value.includes(dir)) {
  backupPickerBreadcrumbs.value = [{ name: dirName, path: dir }];
  } else {
  backupPickerBreadcrumbs.value.push({ name: dirName, path: dir });
  }
  backupPickerCurrentPath.value = dir;
  await loadBackupPickerSubDirs(dir);
}

/** 点击面包屑导航到指定层级 */
function backupPickerNavigateTo(idx: number) {
  backupPickerBreadcrumbs.value = backupPickerBreadcrumbs.value.slice(0, idx + 1);
  const currentPath = backupPickerBreadcrumbs.value[idx].path;
  backupPickerCurrentPath.value = currentPath;
  loadBackupPickerSubDirs(currentPath);
}

/** 加载指定路径下的子目录列表（一层） */
async function loadBackupPickerSubDirs(path: string) {
  backupPickerLoading.value = true;
  try {
  const data = await api.get('/backup/accessible-paths/children', { params: { path } }) as any;
  backupPickerDirs.value = data.dirs || [];
  if (data.error) {
  backupError.value = data.error;
  setTimeout(() => { backupError.value = ''; }, 5000);
  }
  } catch (e) {
  console.error('加载子目录失败:', e);
  backupPickerDirs.value = [];
  } finally {
  backupPickerLoading.value = false;
  }
}

/** 确认选择，将当前路径写回复份配置 */
function confirmBackupPathPick() {
  if (!backupPickerCurrentPath.value) return;
  backupForm.value.target_dir = backupPickerCurrentPath.value;
  showBackupPathPicker.value = false;
}
</script>

<style scoped>
.settings-page {
  height: 100%;
  overflow-y: auto;
  padding: var(--space-6);
  background: var(--bg-secondary);
}

/* Gmail 代理配置卡片 */
.provider-card {
  background: var(--bg-card);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-card);
  overflow: hidden;
  margin-bottom: var(--space-4);
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

.expand-enter-active {
  animation: expandIn 0.3s ease;
}

.expand-leave-active {
  animation: expandIn 0.2s ease reverse;
}

@keyframes expandIn {
  from {
  opacity: 0;
  max-height: 0;
  overflow: hidden;
  }
  to {
  opacity: 1;
  max-height: 2000px;
  overflow: hidden;
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* 移动端适配 */
@media (max-width: 768px) {
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
</style>
