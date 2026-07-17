<template>
  <div class="mail-view">
  <!-- 邮件列表视图 -->
  <div v-if="!selectedMessage" class="mail-list">
  <!-- 工具栏 -->
  <div v-if="!selectMode" class="list-toolbar">
  <div class="toolbar-left">
  <!-- 多选图标按钮 -->
  <button class="btn-icon" @click="enterSelectMode()" title="多选">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
  </svg>
  </button>
  <span class="list-count">聚合 · {{ totalMessages }}封</span>
  <!-- 邮箱筛选下拉框 -->
  <span class="toolbar-divider"></span>
  <select v-if="hasUnifiedAccounts" class="filter-select" v-model="accountFilter" @change="onFilterChange">
  <option value="">全部邮箱</option>
  <option v-for="acc in unifiedAccounts" :key="acc.id" :value="acc.id">
  {{ acc.email }}
  </option>
  </select>
  <!-- 筛选按钮 -->
  <button class="filter-btn" :class="{ active: readFilter === '' && !attachmentFilter }" @click="setReadFilter('')">全部 {{ filterCounts.all }}</button>
  <button class="filter-btn" :class="{ active: readFilter === 'unread' }" @click="setReadFilter('unread')">未读 {{ filterCounts.unread }}</button>
  <button class="filter-btn" :class="{ active: readFilter === 'read' }" @click="setReadFilter('read')">已读 {{ filterCounts.read }}</button>
  <button class="filter-btn" :class="{ active: attachmentFilter }" @click="setAttachmentFilter()">附件 {{ filterCounts.attachments }}</button>
  </div>
  <div class="toolbar-right">
  <!-- 移动端：筛选展开/收起按钮 -->
  <button class="btn-icon mobile-filter-toggle" :class="{ active: hasActiveFilter }" @click="showMobileFilters = !showMobileFilters">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>
  </button>
  <!-- 一键全部已读：聚合视图标记所有聚合邮箱的未读邮件，非聚合邮箱不受影响 -->
  <button v-if="hasUnifiedAccounts" class="btn-icon mark-all-read-btn" :class="{ confirming: markAllReadConfirm }" @click="markAllRead" :title="markAllReadConfirm ? '再次点击确认全部已读' : '全部已读'">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>
  </svg>
  </button>
  <!-- 聚合设置按钮 -->
  <button class="btn-icon" @click="openSettings" title="聚合设置">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
  </svg>
  </button>
  <span class="sync-status" :class="{ connected: wsConnected }" :title="wsConnected ? '实时同步已连接' : '实时同步未连接'">
  <span class="status-dot"></span>
  </span>
  </div>
  <!-- 移动端：筛选下拉菜单（右侧紧凑面板） -->
  <transition name="filter-dropdown">
  <div v-if="showMobileFilters" class="mobile-filter-dropdown">
  <div class="filter-backdrop" @click="showMobileFilters = false"></div>
  <div class="filter-dropdown-menu filter-dropdown-compact">
  <!-- 邮箱下拉选择器 -->
  <template v-if="hasUnifiedAccounts">
  <div class="filter-dropdown-picker" @click.stop="showAccountList = !showAccountList">
  <span class="picker-text">{{ accountFilter ? (unifiedAccounts.find(a => a.id === accountFilter)?.email || '全部邮箱') : '全部邮箱' }}</span>
  <svg class="picker-arrow" :class="{ open: showAccountList }" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
  </div>
  <!-- 邮箱列表（可展开收起） -->
  <transition name="sub-list">
  <div v-if="showAccountList" class="filter-sub-list">
  <button class="filter-dropdown-item" :class="{ active: accountFilter === '' }" @click="accountFilter = ''; onFilterChange(); showAccountList = false">全部邮箱</button>
  <button v-for="acc in unifiedAccounts" :key="acc.id" class="filter-dropdown-item" :class="{ active: accountFilter === acc.id }" @click="accountFilter = acc.id; onFilterChange(); showAccountList = false">{{ acc.email }}</button>
  </div>
  </transition>
  <div class="filter-dropdown-divider"></div>
  </template>
  <!-- 筛选条件 -->
  <button class="filter-dropdown-item" :class="{ active: readFilter === '' && !attachmentFilter }" @click="setReadFilter(''); showMobileFilters = false">全部 {{ filterCounts.all }}</button>
  <button class="filter-dropdown-item" :class="{ active: readFilter === 'unread' }" @click="setReadFilter('unread'); showMobileFilters = false">未读 {{ filterCounts.unread }}</button>
  <button class="filter-dropdown-item" :class="{ active: readFilter === 'read' }" @click="setReadFilter('read'); showMobileFilters = false">已读 {{ filterCounts.read }}</button>
  <button class="filter-dropdown-item" :class="{ active: attachmentFilter }" @click="setAttachmentFilter(); showMobileFilters = false">附件 {{ filterCounts.attachments }}</button>
  </div>
  </div>
  </transition>
  </div>

  <!-- 多选模式工具栏（用 template v-else 包裹） -->
  <template v-else>
  <div class="select-toolbar">
  <button class="select-btn" @click="exitSelectMode">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
  </button>
  <span class="select-info">已选 {{ selectedIds.size }} 封</span>
  <div class="select-actions">
  <button class="select-btn" @click="toggleSelectAll" :title="isAllSelected ? '取消全选' : '全选'">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
  </svg>
  </button>
  <button class="select-btn mark-read" @click="batchMarkRead" :disabled="selectedIds.size === 0" title="标记已读">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>
  </svg>
  </button>
  <button class="select-btn delete" @click="batchDelete" :disabled="selectedIds.size === 0" title="删除选中">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
  </svg>
  </button>
  </div>
  </div>
  </template>

  <!-- 加载中（首次加载无缓存数据时显示） -->
  <div v-if="loading && messages.length === 0" class="list-loading">
  <div class="spinner"></div>
  <span>加载中...</span>
  </div>

  <!-- 空状态：未选择聚合邮箱（后端返回 no_accounts 时显示引导提示） -->
  <div v-else-if="!hasUnifiedAccounts" class="list-empty">
  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.3">
  <rect x="2" y="6" width="20" height="12" rx="2"/><path d="M22 10L12 16L2 10"/><path d="M2 6l10 6 10-6"/>
  </svg>
  <span>暂未选择聚合邮箱，请在设置中选择需要聚合的邮箱账号</span>
  <button class="btn btn-primary btn-add" @click="openSettings">前往设置</button>
  </div>

  <!-- 空状态：已选择聚合邮箱但无邮件 -->
  <div v-else-if="messages.length === 0" class="list-empty">
  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.3">
  <rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 4L12 13L2 4"/>
  </svg>
  <span>暂无邮件</span>
  </div>

  <!-- 邮件列表 -->
  <div v-else class="list-items">
  <button
  v-for="msg in messages"
  :key="msg.id + '-' + msg.account_id"
  class="mail-item"
  :class="{ unread: !msg.is_read, selected: selectMode && selectedIds.has(msg.id + '-' + msg.account_id) }"
  @click="selectMode ? toggleSelect(msg.id + '-' + msg.account_id) : selectMessage(msg)"
  @mouseenter="prefetchMessage(msg)"
  @contextmenu.prevent="enterSelectMode(msg.id + '-' + msg.account_id)"
  >
  <!-- 多选模式下的勾选框 -->
  <div v-if="selectMode" class="check-circle" :class="{ checked: selectedIds.has(msg.id + '-' + msg.account_id) }">
  <svg v-if="selectedIds.has(msg.id + '-' + msg.account_id)" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
  </div>
  <!-- 左列：头像 + 发件人名称 -->
  <div class="mail-sender">
  <div class="mail-avatar" :style="{ background: getAvatarColor(msg.from_addr) }">
  {{ getInitial(msg.from_addr) }}
  </div>
  <span class="mail-from" :title="displayName(msg.from_addr)">{{ displayName(msg.from_addr) }}</span>
  </div>
  <!-- 中列：状态图标 + 主题 + 邮箱标签 + 附件 -->
  <div class="mail-info">
  <div class="mail-main-row">
  <!-- 已读/未读邮件图标 -->
  <svg v-if="!msg.is_read" class="mail-status-icon unread-icon" width="16" height="16" viewBox="0 0 24 24"><path fill="currentColor" d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/></svg>
  <svg v-else class="mail-status-icon read-icon" width="16" height="16" viewBox="0 0 1024 1024" fill="currentColor"><path d="M461.816 79.279c30.333-20.364 69.97-20.373 100.311-0.021l384.19 257.69c9.256 6.208 13.947 16.672 13.216 27.044 0.108 1.548 0.096 3.1-0.034 4.64 0.33 1.778 0.501 3.61 0.501 5.483v495.903C960 919.714 919.706 960 870 960H154c-49.706 0-90-40.286-90-89.982V374.115c0-2.663 0.347-5.245 0.999-7.704-0.004-0.803 0.025-1.608 0.086-2.412-0.804-10.432 3.883-20.985 13.191-27.234z m70.259 519.057c-11.417-10.283-28.76-10.278-40.171 0.012L157.358 900.01h709.674zM124 425.237v424.071L381.796 616.85 124 425.237z m776 0.224L642.268 616.842 900 848.964V425.461zM528.7 129.074a30.005 30.005 30 0 0 0-33.437 0.007L143.678 365.114l283.558 210.762 24.483-22.075c33.891-30.56 85.223-30.88 119.48-0.952l1.034 0.916 24.56 22.121 283.833-210.763z"/></svg>
  <span class="mail-subject">{{ msg.subject || '(无主题)' }}</span>
  <!-- 邮箱身份标识标签（主题后，完整显示） -->
  <span v-if="msg.account_email" class="mail-account-tag" :class="msg.account_provider" :title="msg.account_email">
  {{ msg.account_email }}
  </span>
  <!-- 附件图标 -->
  <svg v-if="msg.has_attachments" class="att-badge" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/></svg>
  </div>
  </div>
  <!-- 已读/未读标签 -->
  <span class="mail-status-tag" :class="msg.is_read ? 'read' : 'unread'">
  {{ msg.is_read ? '已读' : '未读' }}
  </span>
  <!-- 右列：日期（独立固定宽度列，保证最右侧对齐） -->
  <span class="mail-date">{{ formatDate(msg.date) }}</span>
  </button>
  </div>

  <!-- 分页器 -->
  <div v-if="!selectMode && totalPages > 1" class="pagination">
  <button class="page-btn" :disabled="currentPage <= 1" @click="goPage(currentPage - 1)">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
  </button>
  <template v-for="p in pageNumbers" :key="p">
  <span v-if="p === '...'" class="page-ellipsis">...</span>
  <button v-else class="page-btn" :class="{ active: p === currentPage }" @click="goPage(p as number)">{{ p }}</button>
  </template>
  <button class="page-btn" :disabled="currentPage >= totalPages" @click="goPage(currentPage + 1)">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
  </button>
  </div>
  </div>

  <!-- 邮件详情视图 -->
  <div v-else class="mail-detail">
  <div class="detail-toolbar">
  <button class="btn-back" @click="backToList">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="15 18 9 12 15 6"/>
  </svg>
  <span>返回</span>
  </button>
  <div class="detail-actions">
  <button class="btn-action" @click="replyMessage" title="回复邮件">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="9 17 4 12 9 7"/><path d="M20 18v-2a4 4 0 0 0-4-4H4"/>
  </svg>
  <span>回复</span>
  </button>
  <button class="btn-action" @click="forwardMessage" title="转发邮件">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
  </svg>
  <span>转发</span>
  </button>
  <button class="btn-action" @click="printMail" :disabled="printing" title="打印">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>
  </svg>
  <span>{{ printing ? '打印中...' : '打印' }}</span>
  </button>
  <button class="btn-action" :class="{ confirm: deleteConfirm }" @click="onDeleteMessage" :title="deleteConfirm ? '再次点击确认删除' : '删除邮件'">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
  </svg>
  <span>{{ deleteConfirm ? '确认删除' : '删除' }}</span>
  </button>
  </div>
  </div>

  <!-- 标题+正文+附件全部在一个滚动区域内 -->
  <div class="detail-body">
  <div class="detail-header">
  <!-- 主题 -->
  <h2 class="detail-subject">{{ selectedMessage.subject || '(无主题)' }}</h2>

  <!-- 第一行：头像 + 发件人姓名/邮箱 + 加入联系人 + 账号标签 -->
  <div class="detail-sender-row">
  <div class="meta-avatar" :style="{ background: getAvatarColor(selectedMessage.from_addr) }">
  {{ getInitial(selectedMessage.from_addr) }}
  </div>
  <div class="meta-from">
  <span class="from-name">{{ displayName(selectedMessage.from_addr) }}</span>
  <span class="from-email" v-if="displayName(selectedMessage.from_addr) !== selectedMessage.from_addr">&lt;{{ selectedMessage.from_addr }}&gt;</span>
  <button class="btn-add-contact" @click="addToContacts" title="加入联系人">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/>
  </svg>
  </button>
  <span v-if="selectedMessage.account_email" class="detail-account-tag" :class="selectedMessage.account_provider">
  {{ selectedMessage.account_email }}
  </span>
  </div>
  </div>

  <!-- 分割线 -->
  <div class="detail-divider"></div>

  <!-- 灰色信息卡：发件人 / 收件人 / 抄送 / 时间（全宽） -->
  <div class="meta-card">
  <div class="meta-row">
  <span class="meta-row-label">发件人</span>
  <span class="meta-row-value" :title="selectedMessage.from_addr">{{ formatAddressList(selectedMessage.from_addr) }}</span>
  </div>
  <div class="meta-row" v-if="selectedMessage.to_addr">
  <span class="meta-row-label">收件人</span>
  <span class="meta-row-value" :title="selectedMessage.to_addr">{{ formatAddressList(selectedMessage.to_addr) }}</span>
  </div>
  <div class="meta-row" v-if="selectedMessage.cc">
  <span class="meta-row-label">抄送</span>
  <span class="meta-row-value" :title="selectedMessage.cc">{{ formatAddressList(selectedMessage.cc) }}</span>
  </div>
  <div class="meta-row">
  <span class="meta-row-label">时间</span>
  <span class="meta-row-value">{{ formatDetailDate(selectedMessage.date) }}</span>
  </div>
  </div>

  <!-- 分割线（信息卡与正文之间） -->
  <div class="detail-divider"></div>
  </div>

  <div v-if="selectedMessage.body_html || selectedMessage.body_text" v-html="sanitizeHtml(selectedMessage.body_html) || selectedMessage.body_text" class="detail-content" @click="handleMailLinkClick"></div>
  <!-- 正文加载中：显示骨架屏 -->
  <div v-else class="body-skeleton">
  <div class="skeleton-line" style="width: 90%"></div>
  <div class="skeleton-line" style="width: 100%"></div>
  <div class="skeleton-line" style="width: 75%"></div>
  <div class="skeleton-line" style="width: 95%"></div>
  <div class="skeleton-line" style="width: 60%"></div>
  <div class="skeleton-line" style="width: 85%"></div>
  <div class="skeleton-line" style="width: 100%"></div>
  <div class="skeleton-line" style="width: 40%"></div>
  </div>

  <!-- 附件列表（放在正文后面，随正文一起滚动） -->
  <div class="attachment-list" v-if="selectedMessage.attachments && selectedMessage.attachments.length > 0">
  <div class="attachment-header">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/></svg>
  <span>附件 ({{ selectedMessage.attachments.length }})</span>
  </div>
  <div class="attachment-item" v-for="att in selectedMessage.attachments" :key="att.part_number" @click="downloadAttachment(att)">
  <div class="att-icon">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
  </div>
  <div class="att-info">
  <div class="att-name">{{ att.filename || '未命名附件' }}</div>
  <div class="att-meta">{{ formatFileSize(att.size) }}</div>
  </div>
  <div class="att-download">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
  </div>
  </div>
  </div>
  </div>
  </div>

  <!-- 聚合设置面板（弹出层） -->
  <transition name="fade">
  <div v-if="showSettings" class="settings-overlay" @click.self="showSettings = false">
  <div class="settings-panel">
  <div class="settings-header">
  <h3 class="settings-title">聚合设置</h3>
  <button class="settings-close" @click="showSettings = false">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
  </button>
  </div>
  <p class="settings-desc">选择要聚合的邮箱账号</p>
  <div class="settings-list">
  <label v-for="acc in mailStore.accounts" :key="acc.id" class="settings-item">
  <input type="checkbox" :value="acc.id" v-model="settingsSelectedIds" />
  <span class="settings-item-icon" v-html="providerIcon(acc.provider)"></span>
  <span class="settings-item-email">{{ acc.email }}</span>
  </label>
  </div>
  <div class="settings-footer">
  <button class="btn btn-primary" @click="saveSettings">保存</button>
  </div>
  </div>
  </div>
  </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { useMailStore } from '../stores/mail';
import { useUIStore } from '../stores/ui';
import api from '../utils/api';
import { providerIcon } from '../utils/provider';
import { sanitizeHtml, handleMailLinkClick } from '../utils/sanitize';
import { getInitial, getAvatarColor, formatDate, formatDetailDate, formatFileSize, extractEmails, extractName, downloadAttachment as downloadAttachmentFile, formatAddressList } from '../utils/mail-helpers';
import { exportMailToPDF } from '../utils/export-pdf';
import type { Attachment, Message } from '../types/mail';
import { useWebSocket } from '../composables/useWebSocket';
import { buildReplyDraft, buildForwardDraft } from '../composables/useReplyForward';
import { useSelectMode } from '../composables/useSelectMode';
import { useConfirmAction } from '../composables/useConfirmAction';
import { useContactNameMap } from '../composables/useContactNameMap';
import { useContacts } from '../composables/useContacts';

const mailStore = useMailStore();
const uiStore = useUIStore();
const { displayName, loadMap: loadContactMap, reloadMap: reloadContactMap } = useContactNameMap();
const { quickAddContact } = useContacts();

const messages = ref<Message[]>([]);
const selectedMessage = ref<Message | null>(null);
const loading = ref(false);
const totalMessages = ref(0);
const currentPage = ref(1);
const pageSize = 40;
const accountFilter = ref('');
const readFilter = ref('');
const attachmentFilter = ref(false);
const showSettings = ref(false);
const settingsSelectedIds = ref<string[]>([]);
const noAccounts = ref(false);  // 后端返回的"未添加聚合邮箱"标志

// 各筛选条件的计数
const filterCounts = ref({ all: 0, unread: 0, read: 0, attachments: 0 });
const showMobileFilters = ref(false);
const showAccountList = ref(false);
const hasActiveFilter = computed(() => readFilter.value !== '' || attachmentFilter.value || accountFilter.value !== '');

/** 是否已选择聚合邮箱（以后端返回的 no_accounts 标志为准） */
const hasUnifiedAccounts = computed(() => !noAccounts.value);

// 前端内存页缓存：筛选条件 + 页码作为 key，切换时先秒显旧数据再后台刷新
interface MessagePageCache { messages: Message[]; total: number; unreadTotal: number; }
const pageCache = new Map<string, MessagePageCache>();

const totalPages = computed(() => Math.max(1, Math.ceil(totalMessages.value / pageSize)));

/** 生成分页页码数组 */
const pageNumbers = computed(() => {
  const total = totalPages.value;
  const current = currentPage.value;
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const pages: (number | string)[] = [1];
  if (current > 3) pages.push('...');
  const start = Math.max(2, current - 1);
  const end = Math.min(total - 1, current + 1);
  for (let i = start; i <= end; i++) pages.push(i);
  if (current < total - 2) pages.push('...');
  pages.push(total);
  return pages;
});

// 已聚合的账号列表（用于筛选下拉框）
const unifiedAccounts = computed(() => {
  if (mailStore.unifiedAccountIds.length === 0) return [];
  return mailStore.accounts.filter((a: any) => mailStore.unifiedAccountIds.includes(a.id));
});

// 多选模式（使用 composable）
const { selectMode, selectedIds, isAllSelected, enterSelectMode, exitSelectMode, toggleSelect, toggleSelectAll } = useSelectMode(() => messages.value.map(m => m.id + '-' + m.account_id));

// 删除确认（使用 composable，两次点击确认机制）
const { confirmTarget: deleteConfirm, requestConfirm: onDeleteConfirm } = useConfirmAction()
// 全部已读确认（两次点击确认机制，避免误操作）
const { confirmTarget: markAllReadConfirm, requestConfirm: onMarkAllReadConfirm, clearConfirm: clearMarkAllReadConfirm } = useConfirmAction()

// 请求版本号：防止并发请求时旧数据覆盖新数据
let loadVersion = 0;

// WebSocket 实时同步（使用 composable）
const { wsConnected, connect: connectWs, disconnect: disconnectWs } = useWebSocket(handleWsMessage)

/** 处理 WebSocket 业务消息 */
function handleWsMessage(data: any) {
  if (data.type === 'new_mail') {
  // 新邮件通知由 App.vue 的全局 WebSocket 处理；列表等待 cache_updated 再刷新。
  return;
  } else if (data.type === 'cache_updated') {
  // 缓存同步完成：刷新列表
  loadUnifiedMessages();
  mailStore.loadFolderCounts();
  } else if (data.type === 'schedule_success' || data.type === 'schedule_failed') {
  // 通知由 App.vue 统一处理；发送成功后的列表刷新等待 cache_updated。
  return;
  }
}

// ==================== 生命周期 ====================

onMounted(() => {
  loadUnifiedMessages();
  connectWs();
  // 加载联系人映射表，用于邮件列表显示联系人名称
  loadContactMap();
});

onUnmounted(() => {
  disconnectWs();
});

// ==================== 数据加载 ====================

function getPageCacheKey() {
  return `unified::${accountFilter.value}::${readFilter.value}::${attachmentFilter.value}::${currentPage.value}::${pageSize}`;
}

function applyCachedPage(cache: MessagePageCache) {
  messages.value = cache.messages;
  totalMessages.value = cache.total;
}

function saveCurrentPageCache(data: any) {
  pageCache.set(getPageCacheKey(), {
  messages: data.messages || [],
  total: data.total || 0,
  unreadTotal: data.unread_total || 0,
  });
}

/** 加载聚合邮件列表 */
async function loadUnifiedMessages() {
  // 先显示缓存（秒显），再后台刷新
  const cachedPage = pageCache.get(getPageCacheKey());
  if (cachedPage) {
  applyCachedPage(cachedPage);
  }
  const showLoading = !cachedPage && messages.value.length === 0;
  loading.value = showLoading;
  const version = ++loadVersion;
  try {
  const params: Record<string, string | number> = {
  page: currentPage.value,
  page_size: pageSize,
  };
  if (accountFilter.value) params.account_filter = accountFilter.value;
  if (readFilter.value) params.read_filter = readFilter.value;
  if (attachmentFilter.value) params.attachment_filter = 'true';
  const data = await api.get('/messages/unified', { params }) as any;
  if (version !== loadVersion) return;
  // Outlook 连接异常时，后端返回 reconnecting: true，前端展示友好提示
  if (data.reconnecting) {
  uiStore.error('邮箱连接异常，正在重新连接，请稍后再试');
  return;
  }
  // 后端返回 no_accounts=true 表示未添加聚合邮箱
  noAccounts.value = !!data.no_accounts;
  saveCurrentPageCache(data);
  messages.value = data.messages || [];
  totalMessages.value = data.total || 0;
  // 更新各筛选条件的计数
  if (data.filter_counts) {
  filterCounts.value = data.filter_counts;
  }
  } catch (e) {
  if (version !== loadVersion) return;
  console.error('加载聚合邮件失败:', e);
  uiStore.error('加载邮件失败');
  } finally {
  if (version === loadVersion) {
  loading.value = false;
  // 列表加载完成后，后台批量预取当前页邮件正文
  nextTick(() => { prefetchVisibleMessages(); });
  }
  }
}

// ==================== 筛选 ====================

function onFilterChange() {
  currentPage.value = 1;
  pageCache.clear();
  loadUnifiedMessages();
}

function setReadFilter(filter: string) {
  readFilter.value = filter;
  attachmentFilter.value = false;
  currentPage.value = 1;
  pageCache.clear();
  loadUnifiedMessages();
}

function setAttachmentFilter() {
  attachmentFilter.value = !attachmentFilter.value;
  if (attachmentFilter.value) {
  readFilter.value = '';
  }
  currentPage.value = 1;
  pageCache.clear();
  loadUnifiedMessages();
}

// ==================== 分页 ====================

function goPage(page: number) {
  if (page < 1 || page > totalPages.value || page === currentPage.value) return;
  currentPage.value = page;
  loadUnifiedMessages();
}

// ==================== 多选操作 ====================

/** 批量删除（按 account_id 分组调用现有 API） */
async function batchDelete() {
  if (selectedIds.value.size === 0) return;
  try {
  // 按账号分组调用 API（后端接口按单账号操作，需分组后逐账号调用）
  const groups = new Map<string, { ids: string[], folder: string }>();
  for (const compositeId of selectedIds.value) {
  const msg = messages.value.find(m => (m.id + '-' + m.account_id) === compositeId);
  if (!msg) continue;
  const key = msg.account_id || '';
  if (!groups.has(key)) groups.set(key, { ids: [], folder: msg.folder || 'INBOX' });
  groups.get(key)!.ids.push(msg.id);
  }
  // 逐组调用
  for (const [accountId, { ids, folder }] of groups) {
  await api.post('/messages/batch-delete', {
  message_ids: ids,
  account_id: accountId,
  folder: folder,
  });
  }
  exitSelectMode();
  // 删除后重新加载当前页，让后端返回正确的分页数据
  await loadUnifiedMessages();
  mailStore.loadFolderCounts();
  } catch (e) {
  console.error('批量删除失败:', e);
  uiStore.error('批量删除失败');
  }
}

/** 批量标记已读（按 account_id 分组调用现有 API） */
async function batchMarkRead() {
  if (selectedIds.value.size === 0) return;
  try {
  // 按账号分组调用 API（后端接口按单账号操作，需分组后逐账号调用）
  const groups = new Map<string, { ids: string[], folder: string }>();
  for (const compositeId of selectedIds.value) {
  const msg = messages.value.find(m => (m.id + '-' + m.account_id) === compositeId);
  if (!msg) continue;
  const key = msg.account_id || '';
  if (!groups.has(key)) groups.set(key, { ids: [], folder: msg.folder || 'INBOX' });
  groups.get(key)!.ids.push(msg.id);
  }
  for (const [accountId, { ids, folder }] of groups) {
  await api.post('/messages/batch-mark-read', {
  message_ids: ids,
  account_id: accountId,
  folder: folder,
  });
  }
  // 更新本地邮件列表中已选邮件的已读状态
  messages.value = messages.value.map(m =>
  selectedIds.value.has(m.id + '-' + m.account_id) ? { ...m, is_read: true } : m
  );
  // 注意：聚合视图暂不更新侧边栏未读数（侧边栏按单个邮箱显示，聚合视图的未读数变化无法映射到具体邮箱）
  exitSelectMode();
  } catch (e) {
  console.error('批量标记已读失败:', e);
  uiStore.error('标记已读失败');
  }
}

/** 一键全部已读（聚合视图）：标记所有聚合邮箱的 INBOX 未读邮件
 *  只处理参与聚合的邮箱（mailStore.unifiedAccountIds），非聚合邮箱不受影响。
 *  后端通过 UID SEARCH UNSEEN 直接从 IMAP 服务器获取所有未读 UID 并批量标记。
 *  成功后必须清空 pageCache 再重新加载，避免旧分页缓存显示未读状态。
 */
async function markAllRead() {
  // 两次点击确认机制
  if (!onMarkAllReadConfirm('unified')) {
  uiStore.info('再次点击确认将所有聚合邮箱的未读邮件标记为已读');
  return;
  }
  clearMarkAllReadConfirm();
  const accountIds = mailStore.unifiedAccountIds;
  if (!accountIds || accountIds.length === 0) {
  uiStore.error('没有参与聚合的邮箱');
  return;
  }
  uiStore.info('正在标记全部已读...');
  try {
  const res = await api.post('/messages/mark-all-read', {
  account_ids: accountIds,
  folder: 'INBOX',
  });
  const total = res.data?.total_marked ?? 0;
  // 关键：清空前端分页缓存，避免旧缓存显示未读状态
  pageCache.clear();
  // 重新加载聚合列表（此时数据库已全部标记为已读）
  await loadUnifiedMessages();
  // 刷新侧边栏各邮箱未读数（folder_stats.unread_count 已置 0）
  mailStore.loadFolderCounts();
  if (total > 0) {
  uiStore.success(`已标记 ${total} 封邮件为已读`);
  } else {
  uiStore.info('没有未读邮件');
  }
  } catch (e: any) {
  console.error('全部已读失败:', e);
  uiStore.error('全部已读失败：' + (e.response?.data?.detail || e.message || '网络错误'));
  }
}

// ==================== 邮件操作 ====================

/** 选择邮件查看详情（带竞态保护）
 * 1. 用 BODY.PEEK[] 拉取正文（不自动标已读）
 * 2. 如果邮件未读，调用 STORE +FLAGS \Seen 标记已读
 * 3. 更新本地列表中的已读状态和侧边栏未读数
 */
async function selectMessage(msg: Message) {
  const version = ++loadVersion;

  // 乐观 UI：立即用摘要数据渲染头部，正文留空显示骨架屏
  selectedMessage.value = {
  ...msg,
  body_html: '',
  body_text: '',
  attachments: [],
  };

  try {
  const params: Record<string, string> = { folder: msg.folder || 'INBOX' };
  if (msg.account_id) params.account_id = msg.account_id;
  const data = await api.get(`/messages/${msg.id}`, { params }) as any;
  if (version !== loadVersion) return;
  // 详情接口可能不带回 account_id；必须保留列表摘要上的归属账号，
  // 否则回复时 account_id 为空，发件人会错成侧边栏「邮件菜单」选中账号
  selectedMessage.value = {
  ...data,
  account_id: data.account_id || msg.account_id || '',
  account_email: data.account_email || msg.account_email || '',
  account_provider: data.account_provider || msg.account_provider || '',
  };

  // 未读邮件：标记已读
  if (!msg.is_read) {
  const idx = messages.value.findIndex((m: Message) => m.id === msg.id && m.account_id === msg.account_id);
  if (idx !== -1) {
  messages.value[idx] = { ...messages.value[idx], is_read: true };
  }
  api.post('/mark-read', {
  message_id: msg.id,
  folder: msg.folder || 'INBOX',
  account_id: msg.account_id || '',
  }).catch((e: any) => console.error('[UnifiedInbox] 标记已读失败:', e));
  mailStore.decrementUnreadCount(msg.folder || 'INBOX');
  }
  } catch (e: any) {
  if (version !== loadVersion) return;
  console.error('加载邮件详情失败:', e);
  // Outlook 连接异常时，后端返回 503 + { reconnecting: true }
  const respData = e?.response?.data;
  if (respData?.reconnecting) {
  uiStore.error('邮箱连接异常，正在重新连接，请稍后再试');
  } else {
  uiStore.error('加载邮件详情失败');
  }
  }
}

/** 删除邮件（两次点击确认机制） */
async function onDeleteMessage() {
  if (!selectedMessage.value) return;
  // 第一次点击进入确认状态，第二次点击执行删除
  if (!onDeleteConfirm(selectedMessage.value.id)) return;

  try {
  const params: Record<string, string> = { folder: selectedMessage.value.folder || 'INBOX' };
  if (selectedMessage.value.account_id) params.account_id = selectedMessage.value.account_id;
  await api.delete(`/messages/${selectedMessage.value.id}`, { params });
  messages.value = messages.value.filter(m => m.id !== selectedMessage.value!.id);
  totalMessages.value = Math.max(0, totalMessages.value - 1);
  selectedMessage.value = null;
  mailStore.loadFolderCounts();
  } catch (e) {
  console.error('删除邮件失败:', e);
  uiStore.error('删除邮件失败');
  }
}

function backToList() {
  selectedMessage.value = null;
}

/** 快速添加发件人到联系人列表 */
async function addToContacts() {
  if (!selectedMessage.value) return;
  const fromAddr = selectedMessage.value.from_addr || '';
  // 从 from_addr 提取邮箱地址（支持 "姓名 <邮箱>" 和纯邮箱格式）
  const emails = extractEmails(fromAddr);
  if (emails.length === 0) {
  uiStore.error('无法识别发件人邮箱');
  return;
  }
  const email = emails[0];
  // 提取姓名：取尖括号前的部分，没有则用邮箱前缀
  const name = extractName(fromAddr);
  try {
  await quickAddContact(name, email);
  uiStore.success('已加入联系人');
  // 刷新联系人映射表，让邮件列表立即显示联系人名称
  reloadContactMap();
  } catch (e: any) {
  uiStore.error(e?.response?.data?.error || '添加失败');
  }
}

/** 回复邮件：预填收件人+抄送+主题+引用原文，跳转到写邮件
 *
 * 角色模式规则（详见 useReplyForward.ts）：
 * - to = 原发件人 + 原收件人 - 自己
 * - cc = 原抄送人 - 自己
 * - 发件账号使用邮件所在的 account_id
 */
function replyMessage() {
  if (!selectedMessage.value) return;
  const msg = selectedMessage.value;

  // 聚合视图：发件账号必须是邮件所属账号，不能用侧边栏当前选中账号
  const accountId = (msg.account_id || '').trim();
  if (!accountId) {
  uiStore.error('无法确定邮件所属账号，请重新打开邮件后再回复');
  return;
  }
  const currentAccount = mailStore.accounts.find(a => a.id === accountId);
  const myEmail = currentAccount?.email || msg.account_email || '';

  mailStore.setComposeDraft(buildReplyDraft(msg, myEmail, accountId));
  // 通过 App.vue 的 currentView 切换到 compose
  const event = new CustomEvent('flymail-navigate', { detail: 'compose' });
  window.dispatchEvent(event);
}

/** 转发邮件：预填主题+引用原文，收件人留空，跳转到写邮件 */
function forwardMessage() {
  if (!selectedMessage.value) return;
  const msg = selectedMessage.value;
  // 转发同样必须用邮件所属账号作为发件账号
  const accountId = (msg.account_id || '').trim();
  if (!accountId) {
  uiStore.error('无法确定邮件所属账号，请重新打开邮件后再转发');
  return;
  }
  mailStore.setComposeDraft(buildForwardDraft(msg, accountId));
  const event = new CustomEvent('flymail-navigate', { detail: 'compose' });
  window.dispatchEvent(event);
}

/** 打印当前邮件（可通过打印对话框保存为PDF） */
const printing = ref(false);
async function printMail() {
  if (!selectedMessage.value || printing.value) return;
  printing.value = true;
  try {
  await exportMailToPDF(selectedMessage.value);
  // 不显示成功提示：window.print() 无法区分用户是"确认打印"还是"取消"
  // 只有 print() 抛异常时才说明真正出错
  } catch (e: any) {
  console.error('打印失败:', e);
  uiStore.error(e?.message || '打印失败');
  } finally {
  printing.value = false;
  }
}

// 悬停预取：鼠标悬停时静默预取邮件正文，点击时大概率已缓存
let _prefetchTimer: ReturnType<typeof setTimeout> | null = null;
function prefetchMessage(msg: Message) {
  if (_prefetchTimer) return;
  _prefetchTimer = setTimeout(() => { _prefetchTimer = null; }, 300);
  const params: Record<string, string> = { folder: msg.folder || 'INBOX' };
  if (msg.account_id) params.account_id = msg.account_id;
  api.get(`/messages/${msg.id}`, { params }).catch(() => {});
}

// 列表加载完成后，后台批量预取当前页邮件正文
function prefetchVisibleMessages() {
  const ids = messages.value.slice(0, 10).map((m: Message) => m.id);
  if (ids.length === 0) return;
  // 聚合视图邮件来自不同账号，按 account_id 分组预取
  const byAccount: Record<string, string[]> = {};
  for (const m of messages.value.slice(0, 10)) {
  const aid = m.account_id || '';
  if (!byAccount[aid]) byAccount[aid] = [];
  byAccount[aid].push(m.id);
  }
  for (const [accountId, msgIds] of Object.entries(byAccount)) {
  api.post('/prefetch-messages', {
  message_ids: msgIds,
  folder: 'INBOX',
  account_id: accountId,
  }).catch(() => {});
  }
}

// ==================== 聚合设置 ====================

/** 打开设置面板时，初始化选中状态 */
function openSettings() {
  settingsSelectedIds.value = [...mailStore.unifiedAccountIds];
  showSettings.value = true;
}

/** 保存聚合设置 */
async function saveSettings() {
  await mailStore.saveUnifiedSettings(settingsSelectedIds.value);
  showSettings.value = false;
  // 保存后重新加载列表
  currentPage.value = 1;
  loadUnifiedMessages();
}

// ==================== 工具函数 ====================

/** 下载附件（适配器：模板只传 Attachment，补全消息上下文后调用公共工具函数） */
function downloadAttachment(att: Attachment) {
  const msg = selectedMessage.value;
  if (!msg) return;
  downloadAttachmentFile({
  messageId: msg.id,
  accountId: msg.account_id || '',
  folder: msg.folder || 'INBOX',
  partNumber: att.part_number,
  filename: att.filename || 'attachment',
  });
}
</script>

<style scoped>
/* 复用 MailList.vue 的样式结构 */
.mail-view { display: flex; flex-direction: column; height: 100%; overflow: hidden; }
.mail-list { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: var(--bg-primary); }

/* 工具栏 */
.list-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 8px 16px; border-bottom: 1px solid var(--border-color); flex-shrink: 0; }
.toolbar-left { display: flex; align-items: center; gap: var(--space-2); }
.toolbar-right { display: flex; align-items: center; gap: var(--space-3); }
.btn-icon { display: flex; align-items: center; justify-content: center; width: 30px; height: 30px; border: none; border-radius: 8px; background: transparent; color: var(--text-secondary); cursor: pointer; transition: all 0.15s; flex-shrink: 0; }
.btn-icon:hover { background: var(--bg-hover); color: var(--accent-blue); }
/* 全部已读按钮：确认状态高亮提示用户再次点击 */
.mark-all-read-btn.confirming { background: rgba(255, 159, 10, 0.15); color: var(--accent-orange, #ff9500); }
.mark-all-read-btn.confirming:hover { background: rgba(255, 159, 10, 0.25); }
.list-count { font-size: var(--text-xs); color: var(--text-tertiary); font-weight: var(--font-medium); }

/* 实时同步状态 */
.sync-status { display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--text-tertiary); opacity: 0.4; transition: all var(--transition-normal); }
.sync-status.connected .status-dot { background: var(--color-success); opacity: 1; box-shadow: 0 0 4px rgba(52, 199, 89, 0.4); }

/* 工具栏分隔线 */
.toolbar-divider { width: 1px; height: 16px; background: var(--border-color); flex-shrink: 0; margin: 0 4px; }
/* 筛选下拉框和按钮（工具栏内） */
.filter-select { padding: 4px 8px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary); font-size: 12px; font-family: inherit; cursor: pointer; outline: none; max-width: 160px; }
.filter-select:focus { border-color: var(--color-accent); }
.filter-btn { padding: 3px 10px; border: none; border-radius: 4px; background: transparent; color: var(--text-tertiary); font-size: 12px; font-family: inherit; cursor: pointer; transition: all 0.15s; }
.filter-btn:hover { background: var(--bg-hover); color: var(--text-secondary); }
.filter-btn.active { background: rgba(0, 122, 255, 0.1); color: var(--color-accent); font-weight: 500; }

/* 多选工具栏 */
.select-toolbar { display: flex; align-items: center; gap: var(--space-2); padding: 6px 12px; background: var(--bg-secondary); border-bottom: 1px solid var(--border-color); flex-shrink: 0; }
.select-info { flex: 1; font-size: var(--text-sm); color: var(--text-secondary); font-weight: 500; }
.select-actions { display: flex; align-items: center; gap: 4px; }
.select-btn { display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; border: none; border-radius: 8px; background: transparent; color: var(--text-secondary); cursor: pointer; transition: all 0.15s; }
.select-btn:hover { background: var(--bg-hover); color: var(--text-primary); }
.select-btn.delete { color: #FF3B30; }
.select-btn.delete:hover { background: rgba(255, 59, 48, 0.1); }
.select-btn.delete:disabled { color: var(--text-tertiary); opacity: 0.4; cursor: not-allowed; }
.select-btn.mark-read { color: var(--accent-blue, #007AFF); }
.select-btn.mark-read:hover { background: rgba(0, 122, 255, 0.1); }
.select-btn.mark-read:disabled { color: var(--text-tertiary); opacity: 0.4; cursor: not-allowed; }

/* 加载/空状态 */
.list-loading, .list-empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: var(--space-3); color: var(--text-tertiary); font-size: var(--text-sm); }
.btn-add { margin-top: 8px; padding: 8px 20px; font-size: var(--text-sm); }
.spinner { width: 20px; height: 20px; border: 2px solid var(--border-color); border-top-color: var(--color-accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* 邮件列表项 */
.list-items { flex: 1; overflow-y: auto; -webkit-overflow-scrolling: touch; }
.mail-item { display: flex; align-items: center; gap: 0; padding: 10px 16px; border: none; background: transparent; border-bottom: 1px solid var(--border-color); cursor: pointer; transition: background var(--transition-fast); width: 100%; text-align: left; font-family: inherit; min-height: 52px; }
/* 左列：头像 + 发件人名称（名称有充足空间完整显示） */
.mail-sender { display: flex; align-items: center; gap: 10px; flex-shrink: 0; width: 160px; min-width: 0; padding-right: 12px; }
.mail-item:hover { background: var(--bg-hover); }
.mail-item.unread .mail-from { font-weight: var(--font-semibold); color: var(--text-primary); }
.mail-item.unread .mail-subject { color: var(--text-primary); font-weight: var(--font-medium); }
.mail-item.selected { background: rgba(0, 122, 255, 0.1); }

/* 头像 */
.mail-avatar { width: 32px; height: 32px; border-radius: var(--border-radius-full); display: flex; align-items: center; justify-content: center; color: white; font-size: 13px; font-weight: var(--font-semibold); flex-shrink: 0; }
.mail-info { flex: 1; min-width: 0; display: flex; align-items: center; }
.mail-main-row { display: flex; align-items: center; gap: 8px; min-width: 0; flex: 1; }
/* 发件人名称：完整显示，空间不足时截断 */
.mail-from { font-size: 13px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: var(--font-medium); flex: 1; min-width: 0; }
/* 主题：自适应截断，给邮箱标签让位 */
.mail-subject { font-size: 13px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; min-width: 60px; }
.mail-date { font-size: 11px; color: var(--text-tertiary); flex-shrink: 0; white-space: nowrap; width: 70px; text-align: right; }
/* 已读/未读标签（日期前一列，固定宽度） */
.mail-status-tag { flex-shrink: 0; width: 42px; text-align: center; font-size: 10px; font-weight: 500; padding: 1px 0; border-radius: 4px; line-height: 1.5; white-space: nowrap; }
.mail-status-tag.unread { background: rgba(245, 166, 35, 0.12); color: #D48806; }
.mail-status-tag.read { background: rgba(142, 142, 147, 0.1); color: #8E8E93; }

  /* 邮箱身份标识标签（完整显示，不截断） */
.mail-account-tag {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 8px;
  font-weight: 500;
  white-space: nowrap;
  line-height: 1.5;
  flex-shrink: 0;
  letter-spacing: 0.01em;
}
.mail-account-tag.qq { background: rgba(255, 220, 4, 0.18); color: #D4940A; }
.mail-account-tag.gmail { background: rgba(234, 67, 53, 0.1); color: #D93025; }
.mail-account-tag.netease { background: rgba(202, 31, 43, 0.1); color: #C01F2B; }
.mail-account-tag.sina { background: rgba(216, 30, 6, 0.1); color: #D81E06; }
.mail-account-tag.outlook { background: rgba(0, 120, 212, 0.1); color: #0078D4; }
.mail-account-tag.icloud { background: rgba(52, 120, 246, 0.1); color: #3478F6; }

/* 状态图标和附件 */
.mail-status-icon { flex-shrink: 0; display: flex; align-items: center; }
.unread-icon { color: #f5a623; }
.read-icon { color: #c7c7cc; }
.att-badge { flex-shrink: 0; color: var(--text-tertiary, #999); }

/* 勾选圆圈 */
.check-circle { width: 22px; height: 22px; border-radius: 50%; border: 2px solid #c7c7cc; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1); margin-right: 10px; }
.check-circle.checked { background: #007AFF; border-color: #007AFF; transform: scale(1.1); }

/* 分页器 */
.pagination { display: flex; align-items: center; justify-content: center; gap: 4px; padding: 10px 16px; border-top: 1px solid var(--border-color); flex-shrink: 0; background: var(--bg-primary); }
.page-btn { display: flex; align-items: center; justify-content: center; min-width: 32px; height: 32px; border: none; border-radius: 8px; background: transparent; color: var(--text-secondary); font-size: 13px; font-weight: 500; cursor: pointer; transition: all 0.15s; font-family: inherit; padding: 0 6px; }
.page-btn:hover:not(:disabled):not(.active) { background: var(--bg-hover); color: var(--text-primary); }
.page-btn.active { background: #007AFF; color: #fff; font-weight: 600; }
.page-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.page-ellipsis { display: flex; align-items: center; justify-content: center; width: 24px; height: 32px; color: var(--text-tertiary); font-size: 13px; user-select: none; }

/* 邮件详情 */
.mail-detail { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: var(--bg-primary); }
.detail-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 6px 12px; border-bottom: 1px solid var(--border-color); flex-shrink: 0; }
.btn-back { display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px; border: none; border-radius: var(--border-radius-sm); background: var(--bg-secondary); color: var(--text-secondary); font-size: var(--text-xs); font-family: inherit; cursor: pointer; transition: all var(--transition-fast); }
.btn-back:hover { background: var(--bg-tertiary); color: var(--text-primary); }
.detail-actions { display: flex; align-items: center; gap: var(--space-2); }
.btn-action { display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px; border: none; border-radius: var(--border-radius-sm); background: var(--bg-secondary); color: var(--text-secondary); font-size: var(--text-xs); font-family: inherit; cursor: pointer; transition: all var(--transition-fast); }
.btn-action:hover { background: var(--bg-tertiary); color: var(--text-primary); }
.btn-action.confirm { background: #FF3B30; color: #fff; }
.btn-action.confirm:hover { background: #E03A22; }

/* 手机端：详情页工具栏按钮只显示图标，隐藏文字（返回/回复/转发/打印/删除） */
@media (max-width: 768px) {
  .btn-back span,
  .btn-action span { display: none; }
}
.detail-header { padding: var(--space-4) var(--space-5) var(--space-3); }
.detail-subject { font-size: var(--text-xl); font-weight: var(--font-semibold); color: var(--text-primary); line-height: 1.3; margin-bottom: var(--space-3); }
/* 第一行：头像 + 发件人姓名/邮箱 */
.detail-sender-row { display: flex; align-items: center; gap: var(--space-3); }
.meta-avatar { width: 36px; height: 36px; border-radius: var(--border-radius-full); display: flex; align-items: center; justify-content: center; color: white; font-size: var(--text-sm); font-weight: var(--font-semibold); flex-shrink: 0; }
.meta-from { font-size: var(--text-sm); color: var(--text-primary); font-weight: var(--font-medium); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: flex; align-items: center; gap: 6px; min-width: 0; flex: 1; }
.from-name { overflow: hidden; text-overflow: ellipsis; }
.from-email { font-size: 12px; color: var(--text-secondary); font-weight: var(--font-normal); overflow: hidden; text-overflow: ellipsis; }
/* 加入联系人按钮 */
.btn-add-contact { display: inline-flex; align-items: center; justify-content: center; width: 26px; height: 26px; border: none; border-radius: 6px; background: transparent; color: var(--text-tertiary); cursor: pointer; transition: background 0.15s, color 0.15s; flex-shrink: 0; }
.btn-add-contact:hover { background: var(--bg-hover); color: var(--color-accent); }
/* 分割线：头像行 / 信息卡 / 正文 之间 */
.detail-divider { height: 1px; background: var(--border-color, rgba(0, 0, 0, 0.08)); margin: 12px 0; }
/* 邮件信息卡片：灰色背景，全宽 */
.meta-card { width: 100%; box-sizing: border-box; padding: 12px 14px; background: var(--bg-tertiary, rgba(0, 0, 0, 0.03)); border-radius: 10px; display: flex; flex-direction: column; gap: 6px; }
.meta-row { display: flex; align-items: flex-start; gap: 10px; font-size: var(--text-xs); line-height: 1.6; }
.meta-row-label { color: var(--text-tertiary); flex-shrink: 0; width: 48px; font-weight: 500; }
.meta-row-value { color: var(--text-primary); word-break: break-all; flex: 1; min-width: 0; }
.detail-account-tag { font-size: 10px; padding: 1px 7px; border-radius: 10px; font-weight: 500; }
.detail-account-tag.qq { background: rgba(255, 220, 4, 0.18); color: #D4940A; }
.detail-account-tag.gmail { background: rgba(234, 67, 53, 0.1); color: #D93025; }
.detail-account-tag.netease { background: rgba(202, 31, 43, 0.1); color: #C01F2B; }
.detail-account-tag.sina { background: rgba(216, 30, 6, 0.1); color: #D81E06; }
.detail-account-tag.outlook { background: rgba(0, 120, 212, 0.1); color: #0078D4; }
.detail-account-tag.icloud { background: rgba(52, 120, 246, 0.1); color: #3478F6; }
.detail-body { flex: 1; overflow-y: auto; font-size: var(--text-sm); line-height: 1.7; color: var(--text-primary); -webkit-overflow-scrolling: touch; }
.detail-content { padding: var(--space-5); }
.detail-body :deep(img) { max-width: 100%; height: auto; border-radius: var(--border-radius-md); }
.detail-body :deep(a) { color: var(--color-accent); text-decoration: none; }
.detail-body :deep(a:hover) { text-decoration: underline; }

/* 附件列表 */
.attachment-list { margin-top: 16px; padding: 12px; border-top: 1px solid var(--border-primary, #e5e7eb); }
.attachment-header { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; color: var(--text-secondary, #666); margin-bottom: 8px; }
.attachment-item { display: flex; align-items: center; gap: 10px; padding: 8px 12px; border-radius: 8px; background: var(--bg-secondary, #f5f5f5); cursor: pointer; transition: background 0.15s; }
.attachment-item:hover { background: var(--bg-tertiary, #eaeaea); }
.att-icon { flex-shrink: 0; color: var(--text-tertiary, #999); }
.att-info { flex: 1; min-width: 0; }
.att-name { font-size: 13px; font-weight: 500; color: var(--text-primary, #333); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.att-meta { font-size: 11px; color: var(--text-tertiary, #999); margin-top: 2px; }
.att-download { flex-shrink: 0; color: var(--text-tertiary, #999); padding: 4px; border-radius: 4px; transition: color 0.15s; }
.attachment-item:hover .att-download { color: var(--primary, #007aff); }

/* 聚合设置面板 */
.settings-overlay { position: fixed; inset: 0; z-index: 1500; background: rgba(0, 0, 0, 0.15); backdrop-filter: blur(1px); display: flex; align-items: center; justify-content: center; }
.settings-panel { background: var(--bg-card); border-radius: var(--border-radius-lg); box-shadow: var(--shadow-xl); padding: var(--space-6); min-width: 320px; max-width: 420px; animation: slideUp var(--transition-normal); }
.settings-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-3); }
.settings-title { font-size: var(--text-lg); font-weight: var(--font-semibold); color: var(--text-primary); }
.settings-close { display: flex; align-items: center; justify-content: center; width: 24px; height: 24px; border: none; background: rgba(0, 0, 0, 0.05); border-radius: 50%; cursor: pointer; color: var(--text-tertiary); transition: all 0.15s; }
.settings-close:hover { background: rgba(0, 0, 0, 0.1); color: var(--text-secondary); }
.settings-desc { font-size: var(--text-sm); color: var(--text-secondary); line-height: 1.6; margin-bottom: var(--space-4); }
.settings-list { display: flex; flex-direction: column; gap: 4px; margin-bottom: var(--space-5); }
.settings-item { display: flex; align-items: center; gap: var(--space-3); padding: 10px 12px; border-radius: var(--border-radius-md); cursor: pointer; transition: background 0.15s; }
.settings-item:hover { background: var(--bg-hover); }
.settings-item input[type="checkbox"] { width: 16px; height: 16px; accent-color: var(--color-accent); cursor: pointer; }
.settings-item-icon { width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; line-height: 0; }
.settings-item-email { font-size: var(--text-sm); color: var(--text-primary); }
.settings-footer { display: flex; justify-content: flex-end; gap: var(--space-3); }
.btn { padding: 6px 16px; border: none; border-radius: var(--border-radius-md); font-size: var(--text-sm); font-family: inherit; cursor: pointer; transition: all 0.15s; font-weight: 500; }
.btn-secondary { background: var(--bg-tertiary); color: var(--text-secondary); }
.btn-secondary:hover { background: var(--bg-hover); color: var(--text-primary); }
.btn-primary { background: var(--color-accent); color: white; }
.btn-primary:hover { opacity: 0.9; }

@keyframes slideUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

/* 移动端：筛选切换按钮（桌面端隐藏） */
.mobile-filter-toggle { display: none; }

/* 移动端适配 */
@media (max-width: 768px) {
  /* 移动端缩小发件人列宽度，给主题更多空间 */
  .mail-sender { width: 120px; }

  /* 工具栏精简 */
  .list-toolbar { padding: 8px 12px; }
  .toolbar-left .toolbar-divider { display: none; }
  .toolbar-left .filter-btn,
  .toolbar-left .filter-select { display: none; }

  /* 移动端筛选切换按钮 */
  .mobile-filter-toggle { display: flex; }
  .mobile-filter-toggle.active { color: var(--accent-blue); }

  /* 工具栏作为下拉菜单的定位基准 */
  .list-toolbar { position: relative; }

  /* 移动端筛选下拉菜单：相对工具栏定位，在按钮下方展开 */
  .mobile-filter-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 100;
  pointer-events: none;
  }
  .filter-backdrop {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  pointer-events: auto;
  }
  .filter-dropdown-menu {
  position: relative;
  pointer-events: auto;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-color);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  max-height: 60vh;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  }
  /* 紧凑下拉面板：右侧对齐，固定宽度，圆角卡片 */
  .filter-dropdown-compact {
  position: absolute;
  right: 12px;
  top: 8px;
  min-width: 160px;
  max-height: none;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  box-shadow: 0 6px 20px rgba(0,0,0,0.15);
  padding: 4px 0;
  overflow-y: auto;
  max-height: 50vh;
  }
  .filter-dropdown-item {
  display: block;
  width: 100%;
  padding: 10px 16px;
  font-size: 14px;
  text-align: left;
  background: none;
  border: none;
  color: var(--text-primary);
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  }
  .filter-dropdown-item:active { background: var(--bg-secondary); }
  .filter-dropdown-item.active { color: var(--accent-blue); font-weight: 600; }
  .filter-dropdown-divider { height: 1px; background: var(--border-color); margin: 4px 8px; }
  /* 邮箱下拉选择器 */
  .filter-dropdown-picker {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  cursor: pointer;
  }
  .filter-dropdown-picker:active { background: var(--bg-secondary); }
  .picker-text {
  font-size: 14px;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: calc(100% - 20px);
  }
  .picker-arrow {
  flex-shrink: 0;
  transition: transform 0.2s;
  color: var(--text-tertiary);
  }
  .picker-arrow.open { transform: rotate(180deg); }
  /* 邮箱子列表（展开/收起） */
  .filter-sub-list { overflow: hidden; }
  .sub-list-enter-active { animation: subListIn 0.15s ease; }
  .sub-list-leave-active { animation: subListOut 0.1s ease; }
  @keyframes subListIn { from { opacity: 0; max-height: 0; } to { opacity: 1; max-height: 200px; } }
  @keyframes subListOut { from { opacity: 1; max-height: 200px; } to { opacity: 0; max-height: 0; } }

  /* 下拉菜单动画 */
  .filter-dropdown-enter-active { animation: dropIn 0.15s ease; }
  .filter-dropdown-leave-active { animation: dropOut 0.1s ease; }
  @keyframes dropIn { from { opacity: 0; transform: translateY(-4px) scale(0.96); } to { opacity: 1; transform: translateY(0) scale(1); } }
  @keyframes dropOut { from { opacity: 1; transform: translateY(0) scale(1); } to { opacity: 0; transform: translateY(-4px) scale(0.96); } }

  .detail-header { padding: var(--space-3) var(--space-4) var(--space-2); }
  .detail-subject { font-size: var(--text-lg); }
  .detail-content { padding: var(--space-3) var(--space-4); }
}

/* 骨架屏：正文加载中的占位动画 */
.body-skeleton {
  padding: var(--space-5);
}

.skeleton-line {
  height: 14px;
  background: linear-gradient(90deg, var(--bg-tertiary) 25%, var(--bg-hover) 50%, var(--bg-tertiary) 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: 4px;
  margin-bottom: 12px;
}

@keyframes skeleton-loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
