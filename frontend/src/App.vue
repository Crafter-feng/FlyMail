<template>
  <div id="flymail-app">
  <!-- 桌面端：侧边栏布局 -->
  <aside class="sidebar">
  <div class="sidebar-brand">
  <img class="brand-logo" src="/icon.png" alt="FlyMail" />
  <div class="brand-text">
  <span class="brand-name">Fly<span class="brand-accent">Mail</span></span>
  </div>
  <span class="brand-version">v{{ version }}</span>
  </div>

  <nav class="sidebar-nav">
  <!-- 写邮件按钮 -->
  <button class="compose-btn" @click="currentView = 'compose'">
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
  </svg>
  <span>写邮件</span>
  </button>

  <template v-for="item in navItems" :key="item.key">
  <!-- 写邮件已在上方单独按钮，桌面端跳过 -->
  <template v-if="item.key !== 'compose'">
  <!-- 邮件菜单：可展开 -->
  <div v-if="item.key === 'mail'" class="nav-group">
  <button
  class="nav-item"
  :class="{ active: currentView === 'mail' }"
  @click="toggleMailMenu"
  >
  <span class="nav-icon" v-html="item.icon"></span>
  <span class="nav-label">{{ item.label }}</span>
  <svg class="nav-chevron" :class="{ expanded: mailMenuOpen }" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="6 9 12 15 18 9"/>
  </svg>
  </button>
  <!-- 展开的文件夹列表 -->
  <transition name="slide">
  <div v-if="mailMenuOpen && currentView === 'mail'" class="nav-sub">
  <button
  v-for="folder in mailStore.folders"
  :key="folder.path"
  class="nav-sub-item"
  :class="{ active: mailStore.currentFolder === folder.path }"
  @click="selectFolder(folder.path)"
  >
  <span class="folder-dot" :class="getFolderClass(folder.name)"></span>
  <span class="folder-label">{{ mailStore.folderDisplayName(folder.name) }}</span>
  <span v-if="getFolderCount(folder)" class="folder-count">{{ getFolderCount(folder) }}</span>
  </button>
  </div>
  </transition>
  </div>

  <!-- 备份菜单：可展开（结构同邮件菜单） -->
  <div v-else-if="item.key === 'backup'" class="nav-group">
  <button
  class="nav-item"
  :class="{ active: currentView === 'backup' }"
  @click="toggleBackupMenu"
  >
  <span class="nav-icon" v-html="item.icon"></span>
  <span class="nav-label">{{ item.label }}</span>
  <svg class="nav-chevron" :class="{ expanded: backupMenuOpen }" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="6 9 12 15 18 9"/>
  </svg>
  </button>
  <!-- 展开的备份文件夹列表 -->
  <transition name="slide">
  <div v-if="backupMenuOpen && currentView === 'backup'" class="nav-sub">
  <button
  v-for="f in backupStore.folders"
  :key="f.folder"
  class="nav-sub-item"
  :class="{ active: backupStore.currentFolder === f.folder }"
  @click="selectBackupFolder(f.folder)"
  >
  <span class="folder-dot" :class="backupStore.getFolderClass(f.folder)"></span>
  <span class="folder-label">{{ backupStore.folderDisplayName(f.folder) }}</span>
  <span v-if="f.count" class="folder-count">{{ f.count }}</span>
  </button>
  <!-- 无文件夹时的占位提示 -->
  <div v-if="backupStore.folders.length === 0" class="nav-sub-empty">
  暂无备份邮件
  </div>
  </div>
  </transition>
  </div>

  <!-- 其他菜单项 -->
  <button
  v-else
  class="nav-item"
  :class="{ active: currentView === item.key }"
  @click="currentView = item.key"
  >
  <span class="nav-icon" v-html="item.icon"></span>
  <span class="nav-label">{{ item.label }}</span>
  </button>
  </template>
  </template>
  </nav>

  <div class="sidebar-footer">
  <div class="user-avatar" :style="userAvatarStyle">
  <span class="avatar-emoji">👊</span>
  </div>
  <span class="user-name">{{ user?.username || '用户' }}</span>
  </div>
  </aside>

  <!-- 主内容区 -->
  <div class="main-wrapper">
  <header class="topbar">
  <div class="topbar-left">
  <div class="mobile-brand">
  <img class="mobile-logo" src="/icon.png" alt="FlyMail" />
  <span>FlyMail</span>
  </div>
  <h1 class="topbar-title">{{ currentTitle }}</h1>
  </div>
  <div class="topbar-right">
  <!-- 通知铃铛 -->
  <button class="notification-bell" @click="toggleNotificationPanel">
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
  <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
  </svg>
  <span v-if="mailStore.unreadNotificationCount > 0" class="notification-badge">{{ mailStore.unreadNotificationCount > 99 ? '99+' : mailStore.unreadNotificationCount }}</span>
  </button>
  </div>
  </header>

  <main class="content">
  <transition name="fade" mode="out-in">
  <UnifiedInbox v-if="currentView === 'unified'" />
  <MailList v-else-if="currentView === 'mail'" />
  <ComposeEmail v-else-if="currentView === 'compose'" @sent="onMailSent" @discard="onMailDiscard" />
  <AccountList v-else-if="currentView === 'accounts'" />
  <ContactList v-else-if="currentView === 'contacts'" />
  <Backup v-else-if="currentView === 'backup'" />
  <Settings v-else-if="currentView === 'settings'" />
  <About v-else-if="currentView === 'about'" />
  </transition>
  </main>
  </div>

  <!-- 移动端：底部导航栏（4个主菜单 + 其他弹出菜单） -->
  <nav class="bottom-bar">
  <!-- 聚合 -->
  <button class="tab-item" :class="{ active: currentView === 'unified' }" @click="currentView = 'unified'">
  <span class="tab-icon" v-html="mobileNavIcons.unified"></span>
  <span class="tab-label">聚合</span>
  </button>
  <!-- 邮件 -->
  <button class="tab-item" :class="{ active: currentView === 'mail' }" @click="currentView = 'mail'">
  <span class="tab-icon" v-html="mobileNavIcons.mail"></span>
  <span class="tab-label">邮件</span>
  </button>
  <!-- 账号 -->
  <button class="tab-item" :class="{ active: currentView === 'accounts' }" @click="currentView = 'accounts'">
  <span class="tab-icon" v-html="mobileNavIcons.accounts"></span>
  <span class="tab-label">账号</span>
  </button>
  <!-- 其他：点击弹出写信/设置/关于 -->
  <button class="tab-item" :class="{ active: isOtherActive }" @click="showOtherMenu = !showOtherMenu">
  <span class="tab-icon" v-html="mobileNavIcons.other"></span>
  <span class="tab-label">其他</span>
  </button>
  </nav>

  <!-- 其他菜单弹出层（iOS 风格，从底部弹出） -->
  <transition name="other-menu">
  <div v-if="showOtherMenu" class="other-menu-overlay" @click="showOtherMenu = false">
  <div class="other-menu">
  <button class="other-menu-item" @click="currentView = 'compose'; showOtherMenu = false">
  <span class="other-menu-icon" v-html="mobileNavIcons.compose"></span>
  <span>写信</span>
  </button>
  <button class="other-menu-item" @click="currentView = 'contacts'; showOtherMenu = false">
  <span class="other-menu-icon" v-html="mobileNavIcons.contacts"></span>
  <span>联系人</span>
  </button>
  <button class="other-menu-item" @click="currentView = 'backup'; showOtherMenu = false">
  <span class="other-menu-icon" v-html="mobileNavIcons.backup"></span>
  <span>备份</span>
  </button>
  <button class="other-menu-item" @click="currentView = 'settings'; showOtherMenu = false">
  <span class="other-menu-icon" v-html="mobileNavIcons.settings"></span>
  <span>设置</span>
  </button>
  <button class="other-menu-item" @click="currentView = 'about'; showOtherMenu = false">
  <span class="other-menu-icon" v-html="mobileNavIcons.about"></span>
  <span>关于</span>
  </button>
  </div>
  </div>
  </transition>

  <!-- macOS 风格通知面板（右侧滑出抽屉） -->
  <transition name="notif-drawer">
  <div v-if="showNotificationPanel" class="notification-overlay" @click.self="showNotificationPanel = false">
  <div class="notification-drawer">
  <div class="drawer-header">
  <div class="drawer-header-left">
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text-primary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
  <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
  </svg>
  <span class="drawer-title">通知</span>
  <span v-if="mailStore.unreadNotificationCount > 0" class="drawer-badge">{{ mailStore.unreadNotificationCount }}</span>
  </div>
  <div class="drawer-actions">
  <button v-if="mailStore.notifications.length > 0" class="drawer-action-btn" @click="mailStore.markAllNotificationsRead()">全读</button>
  <button v-if="mailStore.notifications.length > 0" class="drawer-action-btn danger" @click="mailStore.clearNotifications()">清空</button>
  <button class="drawer-close-btn" @click="showNotificationPanel = false">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
  </button>
  </div>
  </div>
  <div class="drawer-body" v-if="mailStore.notifications.length > 0">
  <div
  v-for="n in mailStore.notifications"
  :key="n.id"
  class="notif-card"
  :class="{ unread: !n.read }"
  @click="handleNotifClick(n)"
  >
  <div class="notif-avatar">
  <!-- 定时发送成功：绿色对勾图标 -->
  <svg v-if="n.type === 'schedule_success'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#34C759" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
  <!-- 定时发送失败：红色叉号图标 -->
  <svg v-else-if="n.type === 'schedule_failed'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#FF3B30" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
  <!-- 备份成功：绿色归档图标 -->
  <svg v-else-if="n.type === 'backup_success'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#34C759" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 8v13H3V8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg>
  <!-- 备份失败：红色归档图标 -->
  <svg v-else-if="n.type === 'backup_failed'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#FF3B30" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 8v13H3V8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg>
  <!-- 腾讯邮箱图标（企鹅） -->
  <svg v-else-if="n.provider === 'qq'" width="22" height="22" viewBox="0 0 1024 1024"><path d="M211.101867 363.776c-14.933333 66.56-7.466667 133.12 7.466666 192.256 14.933333 51.754667-7.466667 103.509333-52.309333 133.077333-67.285333 36.949333-149.461333-14.805333-156.970667-81.322666C-57.954133 260.266667 255.944533-57.642667 614.728533 8.874667c-209.28 22.186667-366.250667 162.688-403.626666 354.901333z" fill="#FFDC04"/><path d="M532.4672 844.373333c59.818667-22.186667 119.594667-59.136 164.437333-103.509333 37.376-36.992 97.152-44.373333 141.994667-14.805333 67.285333 36.992 67.285333 133.12 7.509333 177.493333-269.098667 229.162667-702.549333 118.272-822.186666-221.866667 112.128 162.688 321.408 221.866667 508.245333 162.688z" fill="#E03A22"/><path d="M794.056533 326.826667a425.173333 425.173333 0 0 0-171.861333-88.746667c-52.352-14.762667-89.728-59.136-89.728-110.933333 0-73.898667 82.218667-125.653333 149.504-96.085334 336.341333 118.314667 455.893333 539.733333 216.746667 813.312 89.685333-177.493333 37.376-391.850667-104.661334-517.546666z" fill="#27AA3A"/><path d="M652.104533 489.472c0-14.805333 0-29.568-7.509333-36.949333 0-7.424 0-7.424-7.466667-14.805334 0-73.941333-44.842667-133.12-127.061333-133.12-82.218667 0-127.061333 59.178667-127.061333 133.12 0 7.381333-7.466667 7.381333-7.466667 14.805334-7.466667 14.762667-7.466667 22.186667-7.466667 29.568v7.381333c-14.933333 7.381333-29.909333 29.568-37.376 51.754667-14.933333 36.949333-14.933333 73.941333-7.466666 73.941333 7.466667 7.381333 22.4-7.381333 37.333333-22.186667 0 22.186667 14.933333 44.373333 29.909333 59.136-14.933333 0-29.866667 14.805333-29.866666 29.568 0 22.186667 29.866667 36.992 74.709333 36.992 37.376 0 67.285333-14.805333 74.752-29.568h7.466667c7.466667 14.762667 37.376 29.568 74.752 29.568s74.752-14.805333 74.752-36.992c0-14.762667-14.933333-22.186667-29.909334-29.568 14.933333-14.762667 29.866667-29.568 37.376-51.754666 14.933333 22.186667 29.866667 29.568 37.376 22.186666 14.933333-7.381333 7.466667-36.949333-7.466667-73.941333-7.466667-22.186667-22.4-44.373333-37.376-51.754667z" fill="#12B7F5"/></svg>
  <svg v-else-if="n.provider === 'gmail'" width="22" height="22" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>
  <svg v-else-if="n.provider === 'netease'" width="22" height="22" viewBox="0 0 1024 1024"><path d="M592.298667 661.76c60.458667-47.573333 67.072-49.92 84.992-27.392 15.573333 19.242667 12.245333 22.741333-91.733334 113.365333-34.688 30.592-63.744 62.293333-63.744 71.381334 0 7.936-8.96 14.762667-19.029333 14.762666-10.026667 0-46.933333 19.285333-81.493333 44.288C353.024 926.890667 227.84 981.333333 184.192 981.333333c-71.466667 0-67.072-71.381333 5.632-91.733333 124.117333-34.090667 251.605333-106.581333 402.432-227.84z m-46.848-200.618667c14.506667-5.717333 39.125333-7.978667 54.826666-5.589333 15.573333 1.109333 51.370667 5.674667 80.426667 9.045333 128.512 14.805333 224.64 132.693333 214.613333 259.626667-5.546667 70.229333-24.576 106.538667-81.578666 158.634667-89.514667 81.536-214.698667 121.216-257.109334 82.688-27.989333-26.112-50.304-81.706667-41.344-103.210667 5.546667-15.914667 10.069333-15.914667 41.344 1.152 70.4 36.266667 171.008-2.261333 229.12-87.296 58.154667-86.186667 33.493333-180.266667-46.933333-180.266667-29.056 0-40.234667-6.741333-51.370667-31.701333-21.333333-44.16-63.744-46.378667-111.829333-4.48-223.530667 196.053333-431.488 302.592-478.421333 245.930667-30.165333-36.224-6.741333-54.357333 117.333333-90.666667 42.538667-12.544 112.938667-49.834667 191.146667-103.168 111.786667-74.752 124.074667-86.058667 119.68-112.170667-4.522667-21.504 0-30.592 20.096-38.528z m-191.146667-410.282666c60.330667-12.458667 257.024-10.24 307.370667 3.328 95.061333 25.002667 110.634667 41.941333 138.666666 160 16.725333 70.272 15.616 101.973333-4.522666 150.698666-22.314667 55.594667-64.853333 69.12-201.216 68.010667-109.610667-1.109333-111.786667 0-130.816 29.44-23.509333 38.442667-118.570667 114.432-160.981334 130.346667-128.512 46.378667-200.106667 50.944-211.285333 14.677333-11.136-35.2 13.397333-56.704 66.005333-56.704 65.834667 0 174.336-44.245333 205.610667-82.773333 12.245333-13.568 4.437333-17.066667-48.085333-21.546667-70.4-5.589333-95.018667-28.330667-108.373334-99.712-12.373333-68.266667 29.056-130.346667 97.152-130.346667 68.096 0 119.637333 44.245333 119.637334 112.512 0 24.736-4.522667 33.813333-22.314667 44.245334-12.245333 6.741333-15.616 13.568-11.136 22.186666 4.522667 6.741333 13.397333 5.589333 22.314667-2.261333 29.056-24.736 44.842667-67.242667 44.842666-110.933333 0-90.666667-74.752-162.133333-171.008-162.133334-96.256 0-171.008 71.466667-171.008 162.133334 0 27.008 6.741333 56.704 15.573334 73.941333 4.522667 7.936 4.522667 10.24-4.522667 10.24-22.314667 0-55.850667 24.736-55.850667 56.704 0 27.008 22.314667 44.245333 55.850667 44.245333 15.573333 0 22.314667-4.48 29.056-15.914666 4.522667-9.045333 11.136-13.568 15.573333-13.568 6.741333 0 11.136 4.48 11.136 13.568 0 15.914667 11.136 24.736 29.056 24.736 15.573333 0 24.576-7.936 24.576-22.186667 0-10.24-6.741333-22.186667-15.573333-27.008-11.136-6.741333-11.136-7.936-4.522667-22.186667 11.136-24.736 15.573333-56.704 15.573333-90.666666 0-101.973333-67.072-171.008-171.008-171.008-103.936 0-171.008 69.034667-171.008 171.008 0 33.962667 4.522667 65.930667 15.573334 90.666666 6.741333 14.250667 6.741333 15.458667-4.522667 22.186667-8.917333 4.821333-15.573333 16.768-15.573333 27.008 0 14.250667 8.917333 22.186667 24.576 22.186667 17.834667 0 29.056-8.821333 29.056-24.736 0-9.045333 4.522667-13.568 11.136-13.568 4.522667 0 11.136 4.48 15.573333 13.568 6.741333 11.434667 13.397333 15.914667 29.056 15.914666 33.536 0 55.850667-17.237333 55.850667-44.245333 0-31.962667-33.536-56.704-55.850667-56.704-8.917333 0-8.917333-2.261333-4.522667-10.24 8.917333-17.237333 15.573333-46.933333 15.573334-73.941333z" fill="#C5161C"/></svg>
  <svg v-else-if="n.provider === 'sina'" width="22" height="22" viewBox="0 0 1024 1024"><path d="M769.92256 503.466667c-40.96-8.618667-21.162667-30.250667-21.162667-30.250667s39.509333-66.218667-8.490666-115.2c-59.306667-60.458667-201.856 7.253333-201.856 7.253333-55.04 17.237333-39.552-7.253333-32.469334-50.432 0-50.389333-16.938667-135.381333-162.346666-84.949333-142.592 51.84-266.837333 228.949333-266.837334 228.949333C-10.792107 576.853333 0.471893 667.648 0.471893 667.648c21.162667 201.6 231.552 256.298667 393.898667 269.269333 172.202667 14.421333 402.346667-60.458667 472.917333-213.12 72.021333-151.210667-56.448-211.669333-97.408-220.330666m-361.386666 377.301333c-170.837333 7.210667-307.797333-79.232-307.797334-195.84 0-116.650667 136.96-208.810667 307.797334-217.472 169.386667-7.168 307.754667 64.853333 307.754666 180.053333 0 116.608-138.368 224.597333-307.754666 233.258667" fill="#D81E06"/><path d="M374.65856 545.237333c-170.837333 20.138667-151.04 184.32-151.04 184.32s-1.450667 51.84 46.549333 77.738667c100.266667 54.741333 203.306667 21.632 255.530667-47.488 50.816-67.712 19.754667-234.752-151.04-214.613333m-43.776 228.992c-32.469333 4.309333-57.898667-14.378667-57.898667-41.770667 0-27.306667 22.613333-56.149333 55.04-59.008 36.693333-2.901333 60.714667 18.688 60.714667 44.629333 0 27.349333-25.386667 53.290667-57.856 56.149334m100.224-87.850667c-11.306667 8.661333-23.978667 7.253333-29.653333-2.858667a25.770667 25.770667 0 0 1 7.082666-33.109333c12.672-10.112 25.386667-7.253333 31.061334 2.858667 7.04 10.069333 2.816 24.490667-8.490667 33.109333" fill="#2C2C2C"/><path d="M1018.413227 412.757333c1.408-2.901333 1.408-7.210667 1.408-10.069333 2.816-15.872 4.224-31.701333 4.224-47.530667C1024.045227 182.357333 885.677227 42.666667 716.29056 42.666667c-24.021333 0-42.368 18.730667-42.368 43.221333 0 24.448 18.346667 43.178667 42.368 43.178667 122.794667 0 221.653333 100.821333 221.653333 226.090666 0 14.378667-1.408 27.349333-4.266666 41.770667v4.266667c0 24.533333 18.346667 43.221333 42.368 43.221333 21.162667 0 38.101333-12.928 42.368-31.658667" fill="#D81E06"/><path d="M885.677227 370.986667c0-5.76 1.408-10.069333 1.408-15.829334 0-95.061333-76.202667-172.8-169.386667-172.8a35.285333 35.285333 0 0 0-35.285333 36.010667c0 20.138667 15.530667 35.968 35.285333 35.968 55.04 0 98.816 44.672 98.816 100.821333 0 4.309333 0 8.618667-1.408 12.970667h1.408c0 1.408-1.408 2.858667-1.408 4.266667 0 20.181333 15.530667 36.053333 35.285333 36.053333 18.346667 0 32.469333-14.421333 33.877334-31.701333v-2.858667c1.408 0 1.408 0 1.408-2.901333 0 1.450667 0 1.450667 0 0" fill="#D81E06"/></svg>
  <svg v-else-if="n.provider === 'icloud'" width="22" height="22" viewBox="0 0 1024 1024"><path d="M791.488 544.095c-1.28-129.695 105.76-191.871 110.528-194.975-60.16-88.032-153.856-100.064-187.232-101.472-79.744-8.064-155.584 46.944-196.064 46.944-40.352 0-102.816-45.76-168.96-44.544-86.912 1.28-167.072 50.528-211.808 128.384-90.304 156.703-23.136 388.831 64.896 515.935 43.008 62.208 94.304 132.064 161.632 129.568 64.832-2.592 89.376-41.952 167.744-41.952s100.416 41.952 169.056 40.672c69.76-1.312 113.984-63.392 156.704-125.792 49.376-72.16 69.728-142.048 70.912-145.632-1.536-0.704-136.064-52.224-137.408-207.136zM662.56 163.52C698.304 120.16 722.432 60 715.84 0c-51.488 2.112-113.888 34.304-150.816 77.536-33.152 38.368-62.144 99.616-54.368 158.432 57.472 4.48 116.128-29.216 151.904-72.448z" fill="currentColor"/></svg>
  <svg v-else-if="n.provider === 'outlook'" width="22" height="22" viewBox="0 0 1024 1024"><path d="M0.10238 51.189762h460.503099v460.503099H0.10238V51.189762z" fill="#F45325"/><path d="M512.204759 51.189762H972.707858v460.503099h-460.503099V51.189762z" fill="#81BD06"/><path d="M0.10238 563.292142h460.503099v460.656668H0.10238v-460.656668z" fill="#04A6EF"/><path d="M512.204759 563.292142H972.707858v460.656668h-460.503099v-460.656668z" fill="#FFBA07"/></svg>
  <!-- 默认邮件图标 -->
  <svg v-else width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#8E8E93" stroke-width="2">
  <rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 4L12 13L2 4"/>
  </svg>
  </div>
  <div class="notif-body">
  <div class="notif-title-row">
  <span class="notif-provider-name">{{ n.type === 'new_mail' ? providerName(n.provider) : (n.type === 'schedule_success' ? '发送成功' : n.type === 'schedule_failed' ? '发送失败' : n.type === 'backup_success' ? '备份成功' : '备份失败') }}</span>
  <span class="notif-dot" v-if="!n.read"></span>
  <span class="notif-time">{{ formatNotifTime(n.time) }}</span>
  </div>
  <div class="notif-desc"><span class="notif-desc-text">{{ n.type === 'new_mail' ? (n.email + ' 收到新邮件') : n.message }}</span></div>
  </div>
  </div>
  </div>
  <div v-else class="drawer-empty">
  <span>暂无通知</span>
  </div>
  </div>
  </div>
  </transition>

  <!-- 全局 Toast 提示 -->
  <div class="toast-container">
  <transition-group name="toast">
  <div
  v-for="t in uiStore.toasts"
  :key="t.id"
  class="toast-item"
  :class="'toast-' + t.type"
  >
  <svg v-if="t.type === 'success'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
  <svg v-else-if="t.type === 'error'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
  <svg v-else-if="t.type === 'warning'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
  <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
  <span>{{ t.message }}</span>
  </div>
  </transition-group>
  </div>

  <!-- 全局 Confirm 确认框 -->
  <div v-if="uiStore.confirmVisible" class="dialog-overlay" @click.self="uiStore.confirmCancel()">
  <div class="confirm-dialog">
  <h3 class="confirm-title">{{ uiStore.confirmOptions.title }}</h3>
  <p class="confirm-message">{{ uiStore.confirmOptions.message }}</p>
  <div class="confirm-actions">
  <button class="btn btn-secondary" @click="uiStore.confirmCancel()">
  {{ uiStore.confirmOptions.cancelText }}
  </button>
  <button
  class="btn"
  :class="uiStore.confirmOptions.danger ? 'btn-danger' : 'btn-primary'"
  @click="uiStore.confirmOk()"
  >
  {{ uiStore.confirmOptions.confirmText }}
  </button>
  </div>
  </div>
  </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { useMailStore } from './stores/mail';
import { useBackupStore } from './stores/backup';
import { useUIStore } from './stores/ui';
import { storeToRefs } from 'pinia';
import { providerName } from './utils/provider';
import { useWebSocket } from './composables/useWebSocket';
import MailList from './views/MailList.vue';
import UnifiedInbox from './views/UnifiedInbox.vue';
import AccountList from './views/AccountList.vue';
import Settings from './views/Settings.vue';
import About from './views/About.vue';
import ComposeEmail from './views/ComposeEmail.vue';
import ContactList from './views/ContactList.vue';
import Backup from './views/Backup.vue';

const mailStore = useMailStore();
const backupStore = useBackupStore();
const uiStore = useUIStore();
const { user } = storeToRefs(mailStore);
const version = import.meta.env.VITE_APP_VERSION || '0.0.0';
// 从 sessionStorage 恢复上次浏览的页面，刷新后不会回到默认页
const currentView = ref(sessionStorage.getItem('flymail_view') || 'unified');
const mailMenuOpen = ref(true);
const backupMenuOpen = ref(true);
const showNotificationPanel = ref(false);
// 移动端"其他"菜单弹出控制
const showOtherMenu = ref(false);
// "其他"菜单激活状态：当前视图为写信/设置/关于时高亮
const isOtherActive = computed(() => ['compose', 'contacts', 'backup', 'settings', 'about'].includes(currentView.value));

// 移动端底部导航图标（独立于桌面端 navItems，避免耦合）
const mobileNavIcons = {
  unified: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="7" cy="7" r="3"/><circle cx="17" cy="7" r="3"/><circle cx="7" cy="17" r="3"/><circle cx="17" cy="17" r="3"/><line x1="10" y1="7" x2="14" y2="7"/><line x1="7" y1="10" x2="7" y2="14"/><line x1="17" y1="10" x2="17" y2="14"/><line x1="10" y1="17" x2="14" y2="17"/></svg>',
  mail: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 4L12 13L2 4"/></svg>',
  accounts: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
  other: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="5" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="19" cy="12" r="1.5"/></svg>',
  compose: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>',
  settings: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
  about: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
  contacts: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
  backup: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>',
};

const { connect: connectGlobalWs, disconnect: disconnectGlobalWs } = useWebSocket(handleGlobalWsMessage);

/** 切换通知面板 */
function toggleNotificationPanel() {
  showNotificationPanel.value = !showNotificationPanel.value;
}

/** 点击单条通知：标记已读 + 跳转到对应文件夹 */
function handleNotifClick(n: any) {
  mailStore.markNotificationRead(n.id);
  // 跳转到邮件页面并选中收件箱
  currentView.value = 'mail';
  mailStore.setFolder('INBOX');
}

/** 处理全局 WebSocket 消息：通知中心、顶栏铃铛、账号状态 */
function handleGlobalWsMessage(data: any) {
  if (data.type === 'new_mail') {
  if (data.provider && data.email) {
  mailStore.addNotification(data.provider, data.email, data.folder || 'INBOX', data.notification_id);
  }
  if (!data.account_id || data.account_id === mailStore.currentAccountId) {
  mailStore.loadFolderCounts();
  }
  } else if (data.type === 'schedule_success' || data.type === 'schedule_failed') {
  mailStore.addNotification(
  data.provider || '', data.email || '', '', data.notification_id,
  data.type, data.message || ''
  );
  if (data.type === 'schedule_success' && (!data.account_id || data.account_id === mailStore.currentAccountId)) {
  mailStore.loadFolderCounts();
  }
  } else if (data.type === 'backup_success' || data.type === 'backup_failed') {
  // 备份结果通知（仅手动点击"立即备份"时推送）
  mailStore.addNotification(
  data.provider || '', data.email || '', '', data.notification_id,
  data.type, data.message || ''
  );
  } else if (data.type === 'connection_status') {
  const account = mailStore.accounts.find((a: any) => a.id === data.account_id);
  if (data.status === 'reauth_needed' && data.account_id) {
  mailStore.reauthAccountIds.add(data.account_id);
  }
  if (account) {
  if (data.status === 'reauth_needed') {
  account.status = 'reauth_needed';
  } else {
  account.status = data.status === 'connected' ? 'connected' : 'error';
  if (data.status === 'connected') {
  mailStore.reauthAccountIds.delete(data.account_id);
  }
  }
  }
  }
}

/** 写邮件发送完成后，跳转回收件箱 */
function onMailSent() {
  currentView.value = 'unified';
  uiStore.success('邮件发送成功');
}

/** 丢弃写邮件，返回上一视图 */
function onMailDiscard() {
  currentView.value = 'unified';
}

/** 格式化通知时间（macOS 风格：刚刚 / X分钟前 / X小时前 / 日期） */
function formatNotifTime(timestamp: number): string {
  const now = Date.now();
  const diff = now - timestamp;
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return '刚刚';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}小时前`;
  const date = new Date(timestamp);
  return `${date.getMonth() + 1}月${date.getDate()}日 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
}

// 导航项配置
const navItems = [
  {
  key: 'compose',
  label: '写邮件',
  shortLabel: '写信',
  icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>',
  },
  {
  key: 'unified',
  label: '聚合',
  shortLabel: '聚合',
  icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="7" cy="7" r="3"/><circle cx="17" cy="7" r="3"/><circle cx="7" cy="17" r="3"/><circle cx="17" cy="17" r="3"/><line x1="10" y1="7" x2="14" y2="7"/><line x1="7" y1="10" x2="7" y2="14"/><line x1="17" y1="10" x2="17" y2="14"/><line x1="10" y1="17" x2="14" y2="17"/></svg>',
  },
  {
  key: 'mail',
  label: '邮件',
  shortLabel: '邮件',
  icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 4L12 13L2 4"/></svg>',
  },
  {
  key: 'accounts',
  label: '账号',
  shortLabel: '账号',
  icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
  },
  {
  key: 'contacts',
  label: '联系人',
  shortLabel: '联系人',
  icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
  },
  {
  key: 'backup',
  label: '备份',
  shortLabel: '备份',
  icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>',
  },
  {
  key: 'settings',
  label: '设置',
  shortLabel: '设置',
  icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
  },
  {
  key: 'about',
  label: '关于',
  shortLabel: '关于',
  icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
  },
];

// 当前页面标题
const currentTitle = computed(() => {
  if (currentView.value === 'unified') return '聚合';
  if (currentView.value === 'mail') {
  return mailStore.currentFolderName || '邮件';
  }
  const item = navItems.find(i => i.key === currentView.value);
  return item?.label || '';
});

// 根据用户名生成确定性头像颜色
const userAvatarStyle = computed(() => {
  const name = mailStore.user?.username || '用户';
  const colors = ['#3B82F6', '#8B5CF6', '#EC4899', '#F59E0B', '#10B981', '#EF4444', '#6366F1', '#14B8A6'];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
  hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  const color = colors[Math.abs(hash) % colors.length];
  return {
  background: color,
  color: '#fff',
  fontSize: '14px',
  fontWeight: '600',
  };
});

/** 切换邮件菜单展开/收起 */
function toggleMailMenu() {
  if (currentView.value !== 'mail') {
  currentView.value = 'mail';
  mailMenuOpen.value = true;
  } else {
  mailMenuOpen.value = !mailMenuOpen.value;
  }
}

/** 选择文件夹 */
function selectFolder(path: string) {
  mailStore.setFolder(path);
}

/** 切换备份菜单展开/收起（逻辑同邮件菜单） */
function toggleBackupMenu() {
  if (currentView.value !== 'backup') {
  currentView.value = 'backup';
  backupMenuOpen.value = true;
  // 进入备份页时加载文件夹列表
  backupStore.loadFolders();
  } else {
  backupMenuOpen.value = !backupMenuOpen.value;
  }
}

/** 选择备份文件夹 */
function selectBackupFolder(folder: string) {
  backupStore.setFolder(folder);
}

/** 获取文件夹显示的数量
 *
 * 收件箱显示未读数，其他文件夹显示邮件总数
 */
function getFolderCount(folder: any): number {
  if (folder.name === '收件箱') {
  return folder.unread_count || 0;
  }
  return folder.total_count || 0;
}

/** 根据文件夹显示名返回样式类名
 *
 * 所有邮箱provider的后端都已统一返回中文显示名（收件箱、已发送、草稿箱、垃圾邮件、已删除），
 * 所以这里用显示名匹配即可，不再依赖各provider不同的Modified UTF-7路径。
 */
function getFolderClass(name: string): string {
  const map: Record<string, string> = {
  '收件箱': 'inbox',
  '已发送': 'sent',
  '草稿箱': 'drafts',
  '垃圾邮件': 'junk',
  '已删除': 'trash',
  // 英文名兼容（部分provider可能返回英文名）
  'INBOX': 'inbox',
  'Sent': 'sent',
  'Sent Messages': 'sent',
  'Sent Items': 'sent',
  'Drafts': 'drafts',
  'Junk': 'junk',
  'Junk Email': 'junk',
  'Spam': 'junk',
  'Trash': 'trash',
  'Deleted Messages': 'trash',
  'Deleted Items': 'trash',
  '[Gmail]/Sent Mail': 'sent',
  '[Gmail]/Drafts': 'drafts',
  '[Gmail]/Trash': 'trash',
  '[Gmail]/Spam': 'junk',
  };
  return map[name] || 'default';
}

onMounted(() => {
  connectGlobalWs();
  mailStore.fetchUser();
  mailStore.loadAccounts().then(() => {
  mailStore.loadFolders();
  mailStore.loadUnifiedSettings();
  });
  // 从数据库加载通知记录（刷新页面后通知不丢失）
  mailStore.loadNotifications();
  // 检测OAuth回调参数（Google/Microsoft授权后浏览器重定向回前端页面）
  handleOAuthCallback();
  // 监听弹出窗口发来的 OAuth 结果通知（window.open 打开的授权窗口通过 postMessage 回传结果）
  window.addEventListener('message', handleOAuthPostMessage);
  // 监听子视图的导航事件（回复/转发邮件时切换到写邮件视图）
  window.addEventListener('flymail-navigate', (e: any) => {
  currentView.value = e.detail;
  });
});

// 组件卸载时清理 OAuth 消息监听，防止内存泄漏
onUnmounted(() => {
  disconnectGlobalWs();
  window.removeEventListener('message', handleOAuthPostMessage);
});

/** 检测并处理OAuth回调结果
 *
 * OAuth 授权在 window.open() 打开的新窗口中完成，后端在 TCP 51010 端口处理回调后
 * 展示轻量结果页，结果页通过 window.opener.postMessage() 通知原窗口。
 * 原窗口在 handleOAuthPostMessage() 中接收通知并刷新账号列表。
 *
 * 此函数保留对 URL 参数的检测（兼容直接访问场景），但正常 OAuth 流程不会走到这里。
 */
function handleOAuthCallback() {
  const urlParams = new URLSearchParams(window.location.search);
  const provider = urlParams.get('provider') || 'gmail';
  const pName = providerName(provider);

  // 兼容：直接访问场景下 URL 带有 OAuth 参数
  const oauthSuccess = urlParams.get('oauth_success');
  const oauthEmail = urlParams.get('email');
  if (oauthSuccess === '1') {
  uiStore.success(`${pName}账号添加成功：` + (oauthEmail || ''));
  sessionStorage.setItem('flymail_oauth_just_added', '1');
  currentView.value = 'accounts';
  mailStore.loadAccounts();
  cleanOAuthParams();
  return;
  }

  const oauthError = urlParams.get('oauth_error');
  if (oauthError) {
  uiStore.error(`${pName}授权失败：` + oauthError);
  cleanOAuthParams();
  }
}

/** 监听 OAuth 弹出窗口发来的结果（postMessage 通信）
 *
 * OAuth 授权在 window.open() 打开的新窗口中完成，后端展示轻量结果页后，
 * 结果页中的 JavaScript 通过 window.opener.postMessage() 通知原窗口，
 * 原窗口收到通知后刷新账号列表并设置 flymail_oauth_just_added 标记，
 * 避免账号页立即做连接测试导致误报 invalid token。
 */
function handleOAuthPostMessage(event: MessageEvent) {
  const data = event.data;
  if (!data || typeof data !== 'object') return;

  if (data.type === 'flymail_oauth_success') {
  const pName = providerName(data.provider || 'gmail');
  // 判断是重新授权还是新增账号
  const isReauth = sessionStorage.getItem('flymail_oauth_reauth') === '1';
  sessionStorage.removeItem('flymail_oauth_reauth');

  if (isReauth) {
  uiStore.success(`${pName}重新授权成功`);
  // 重新授权后重载账号数据，刷新邮件列表
  mailStore.loadAccounts().then(() => {
  mailStore.loadFolderCounts();
  });
  sessionStorage.removeItem('flymail_oauth_just_added');
  } else {
  uiStore.success(`${pName}账号添加成功：` + (data.email || ''));
  sessionStorage.setItem('flymail_oauth_just_added', '1');
  currentView.value = 'accounts';
  mailStore.loadAccounts();
  }
  window.removeEventListener('message', handleOAuthPostMessage);
  } else if (data.type === 'flymail_oauth_error') {
  const pName = providerName(data.provider || 'gmail');
  uiStore.error(`${pName}授权失败：` + (data.error || '未知错误'));
  window.removeEventListener('message', handleOAuthPostMessage);
  }
}

/** 清理URL中的OAuth回调参数 */
function cleanOAuthParams() {
  const url = new URL(window.location.href);
  const paramsToClean = ['oauth_success', 'oauth_error', 'email', 'provider'];
  let hasParams = false;
  for (const p of paramsToClean) {
  if (url.searchParams.has(p)) {
  url.searchParams.delete(p);
  hasParams = true;
  }
  }
  if (hasParams) {
  window.history.replaceState({}, '', url.pathname + (url.search || ''));
  }
}

// 切换到邮件/备份页时自动展开菜单
watch(currentView, (v) => {
  if (v === 'mail') mailMenuOpen.value = true;
  if (v === 'backup') {
  backupMenuOpen.value = true;
  backupStore.loadFolders();
  }
  // 保存当前页面到 sessionStorage，刷新后可恢复
  sessionStorage.setItem('flymail_view', v);
});

// ==================== 通知文本溢出检测（跑马灯效果） ====================
// 当通知描述文本超出容器宽度时，添加 marquee class 触发 CSS 滚动动画
// 滚动距离通过 CSS 变量 --marquee-distance 动态设置（像素值）
function applyMarqueeToNotifications() {
  // 仅在通知面板打开时检测，避免无意义的 DOM 查询
  if (!showNotificationPanel.value) return;
  // 查询所有通知描述容器
  const descEls = document.querySelectorAll<HTMLElement>('.notif-desc');
  descEls.forEach((descEl) => {
  const textEl = descEl.querySelector<HTMLElement>('.notif-desc-text');
  if (!textEl) return;
  // 移除旧 class，重新测量（通知内容可能变化）
  textEl.classList.remove('marquee');
  // 强制重排以获取真实 scrollWidth
  void textEl.offsetWidth;
  // 文字宽度超过容器宽度才需要滚动
  const overflow = descEl.scrollWidth - descEl.clientWidth;
  if (overflow > 0) {
  // 设置 CSS 变量供 @keyframes 使用（多滚动 8px 留出视觉余量）
  textEl.style.setProperty('--marquee-distance', `${overflow + 8}px`);
  textEl.classList.add('marquee');
  }
  });
}

// 监听通知列表变化：新通知到来时重新检测溢出
watch(
  () => mailStore.notifications.length,
  () => {
  nextTick(applyMarqueeToNotifications);
  }
);

// 监听面板打开：打开时检测所有已存在通知的溢出
watch(showNotificationPanel, (open) => {
  if (open) {
  nextTick(applyMarqueeToNotifications);
  }
});
</script>

<style scoped>
#flymail-app {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* 侧边栏 */
.sidebar {
  width: var(--sidebar-width);
  height: 100vh;
  background: var(--bg-sidebar);
  backdrop-filter: blur(20px) saturate(180%);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  user-select: none;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-5) var(--space-5) var(--space-4);
}

.brand-logo {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  flex-shrink: 0;
}

.brand-text {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.brand-name {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.5px;
  line-height: 1.2;
  color: var(--text-primary);
}

.brand-accent {
  color: var(--color-accent);
}

.brand-version {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  font-variant-numeric: tabular-nums;
  align-self: flex-end;
  margin-top: auto;
  padding-bottom: 2px;
}

.sidebar-nav {
  flex: 1;
  padding: var(--space-2) var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

/* 写邮件按钮 */
.compose-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 16px;
  margin-bottom: var(--space-2);
  border: none;
  border-radius: var(--border-radius-lg, 8px);
  background: var(--accent-blue, #007AFF);
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.compose-btn:hover {
  opacity: 0.9;
  transform: scale(1.01);
}

.nav-group {
  display: flex;
  flex-direction: column;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 10px 14px;
  border: none;
  background: transparent;
  border-radius: var(--border-radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  color: #3A3A3C;
  font-size: 14px;
  font-weight: var(--font-medium);
  font-family: inherit;
  width: 100%;
  text-align: left;
}

.nav-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--bg-active);
  color: var(--color-accent);
}

.nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.nav-label {
  flex: 1;
  white-space: nowrap;
}

.nav-chevron {
  flex-shrink: 0;
  transition: transform 0.2s ease;
  opacity: 0.5;
}

.nav-chevron.expanded {
  transform: rotate(180deg);
}

/* 子菜单（文件夹列表） */
.nav-sub {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding-left: var(--space-5);
  padding-top: var(--space-1);
  padding-bottom: var(--space-1);
}

.nav-sub-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 7px 12px;
  border: none;
  background: transparent;
  border-radius: var(--border-radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  color: #48484A;
  font-size: 13px;
  font-family: inherit;
  text-align: left;
  width: 100%;
}

.nav-sub-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.nav-sub-item.active {
  background: var(--bg-active);
  color: var(--color-accent);
  font-weight: var(--font-medium);
}

/* 文件夹圆点指示器 */
.folder-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--text-tertiary);
}

.folder-dot.inbox { background: #007AFF; }
.folder-dot.sent { background: #34C759; }
.folder-dot.drafts { background: #FF9500; }
.folder-dot.junk { background: #FF3B30; }
.folder-dot.trash { background: #8E8E93; }
.folder-dot.default { background: var(--text-tertiary); }

.folder-label {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 文件夹数量标签 */
.folder-count {
  font-size: 11px;
  font-weight: var(--font-medium);
  color: var(--text-tertiary);
  background: var(--bg-tertiary);
  border-radius: 10px;
  padding: 1px 7px;
  flex-shrink: 0;
  margin-left: auto;
  min-width: 20px;
  text-align: center;
  line-height: 16px;
}

.nav-sub-item.active .folder-count {
  background: rgba(0, 122, 255, 0.12);
  color: var(--color-accent);
}

/* 备份文件夹列表为空时的占位提示 */
.nav-sub-empty {
  padding: 12px 16px;
  color: var(--text-tertiary, #8E8E93);
  font-size: 12px;
  text-align: center;
}

/* 子菜单展开/收起动画 */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  max-height: 0;
}

.slide-enter-to,
.slide-leave-from {
  opacity: 1;
  max-height: 300px;
}

.sidebar-footer {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  border-top: 1px solid var(--border-color);
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--border-radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  user-select: none;
}

.avatar-emoji {
  font-size: 18px;
  line-height: 1;
}

.user-name {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 主内容区 */
.main-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100vh;
}

.topbar {
  height: var(--header-height);
  background: var(--bg-header);
  backdrop-filter: blur(20px) saturate(180%);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-6);
  flex-shrink: 0;
}

.topbar-left {
  display: flex;
  align-items: center;
}

.topbar-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.topbar-right {
  display: flex;
  align-items: center;
}

/* 移动端品牌（桌面端隐藏） */
.mobile-brand {
  display: none;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}

.mobile-logo {
  width: 24px;
  height: 24px;
  border-radius: 5px;
}

.content {
  flex: 1;
  overflow: hidden;
}

/* 底部导航（桌面端隐藏） */
.bottom-bar {
  display: none;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: var(--bottom-bar-height);
  background: var(--bg-header);
  backdrop-filter: blur(20px) saturate(180%);
  border-top: 1px solid var(--border-color);
  align-items: center;
  padding-bottom: env(safe-area-inset-bottom, 0);
  z-index: 100;
}

.tab-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  height: 100%;
  border: none;
  background: transparent;
  cursor: pointer;
  transition: color var(--transition-fast);
  color: var(--text-tertiary);
  font-family: inherit;
  -webkit-tap-highlight-color: transparent;
}

.tab-item:active {
  color: var(--text-secondary);
}

.tab-item.active {
  color: var(--color-accent);
}

.tab-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 26px;
  transition: transform 0.15s ease;
}

.tab-item.active .tab-icon {
  transform: scale(1.1);
}

.tab-icon svg {
  width: 22px;
  height: 22px;
}

.tab-label {
  font-size: 11px;
  font-weight: var(--font-medium);
}

/* ==================== 移动端"其他"弹出菜单 ==================== */
.other-menu-overlay {
  position: fixed;
  inset: 0;
  z-index: 99;
}

.other-menu {
  position: fixed;
  bottom: calc(var(--bottom-bar-height) + 8px);
  right: 12px;
  background: var(--bg-card);
  border-radius: 14px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.18);
  padding: 4px;
  min-width: 150px;
  z-index: 100;
  overflow: hidden;
}

.other-menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border: none;
  background: transparent;
  border-radius: 10px;
  cursor: pointer;
  color: var(--text-primary);
  font-size: 15px;
  font-family: inherit;
  width: 100%;
  text-align: left;
  transition: background 0.15s;
}

.other-menu-item:active {
  background: var(--bg-hover);
}

.other-menu-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  color: var(--text-secondary);
}

/* 弹出/收起动画 */
.other-menu-enter-active { animation: otherMenuIn 0.2s ease; }
.other-menu-leave-active { animation: otherMenuOut 0.15s ease; }

@keyframes otherMenuIn {
  from { opacity: 0; transform: translateY(8px) scale(0.95); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes otherMenuOut {
  from { opacity: 1; transform: translateY(0) scale(1); }
  to { opacity: 0; transform: translateY(8px) scale(0.95); }
}

/* 页面切换动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Toast 提示 */
.toast-container {
  position: fixed;
  top: var(--space-5);
  right: var(--space-5);
  z-index: 2000;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  pointer-events: none;
}

.toast-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 10px 18px;
  border-radius: var(--border-radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  box-shadow: var(--shadow-lg);
  pointer-events: auto;
  max-width: 380px;
  word-break: break-word;
}

.toast-success { background: var(--color-success); color: white; }
.toast-error { background: var(--color-danger); color: white; }
.toast-warning { background: var(--color-warning); color: white; }
.toast-info { background: var(--bg-card); color: var(--text-primary); border: 1px solid var(--border-color-strong); }

.toast-enter-active { animation: toastIn 0.3s ease; }
.toast-leave-active { animation: toastOut 0.25s ease; }

@keyframes toastIn {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes toastOut {
  from { opacity: 1; transform: translateX(0); }
  to { opacity: 0; transform: translateX(20px); }
}

/* Confirm 确认框 */
.confirm-dialog {
  background: var(--bg-card);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-xl);
  padding: var(--space-6);
  min-width: 320px;
  max-width: 420px;
  animation: slideUp var(--transition-normal);
}

.confirm-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin-bottom: var(--space-3);
}

.confirm-message {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: var(--space-5);
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}

/* 通知铃铛按钮 */
.notification-bell {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  border-radius: 50%;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s ease;
}

.notification-bell:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.notification-badge {
  position: absolute;
  top: 2px;
  right: 2px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 8px;
  background: #FF3B30;
  color: white;
  font-size: 10px;
  font-weight: 600;
  line-height: 16px;
  text-align: center;
  pointer-events: none;
  animation: badgePop 0.3s ease;
}

@keyframes badgePop {
  0% { transform: scale(0); }
  60% { transform: scale(1.2); }
  100% { transform: scale(1); }
}

/* 右侧滑出通知抽屉 */
.notification-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1500;
  background: rgba(0, 0, 0, 0.15);
  backdrop-filter: blur(1px);
}

.notification-drawer {
  position: absolute;
  top: 0;
  right: 0;
  width: 320px;
  height: 100vh;
  background: rgba(246, 246, 246, 0.92);
  backdrop-filter: blur(50px) saturate(180%);
  box-shadow: -4px 0 30px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 抽屉头部 */
.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 20px 16px;
  border-bottom: 0.5px solid rgba(0, 0, 0, 0.06);
  flex-shrink: 0;
}

.drawer-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.drawer-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.2px;
}

.drawer-badge {
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: #FF3B30;
  color: white;
  font-size: 11px;
  font-weight: 600;
  line-height: 18px;
  text-align: center;
}

.drawer-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.drawer-action-btn {
  border: none;
  background: transparent;
  color: var(--color-accent);
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.15s;
}

.drawer-action-btn:hover {
  background: rgba(0, 122, 255, 0.08);
}

.drawer-action-btn.danger {
  color: #FF3B30;
}

.drawer-action-btn.danger:hover {
  background: rgba(255, 59, 48, 0.08);
}

.drawer-close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 50%;
  cursor: pointer;
  color: var(--text-tertiary);
  transition: all 0.15s;
  margin-left: 4px;
}

.drawer-close-btn:hover {
  background: rgba(0, 0, 0, 0.1);
  color: var(--text-secondary);
}

/* 通知列表 */
.drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 12px;
}

.notif-card {
  display: flex;
  gap: 12px;
  padding: 12px;
  border-radius: 12px;
  margin-bottom: 4px;
  transition: all 0.25s ease;
  cursor: pointer;
  position: relative;
  border-left: 3px solid transparent;
}

.notif-card:hover {
  background: rgba(255, 255, 255, 0.7);
}

.notif-card.unread {
  background: rgba(255, 255, 255, 0.85);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  border-left-color: var(--color-accent);
}

.notif-card.unread:hover {
  background: rgba(255, 255, 255, 0.95);
}

/* 已读通知：整体变淡 */
.notif-card:not(.unread) {
  opacity: 0.55;
}

.notif-card:not(.unread):hover {
  opacity: 0.75;
}

.notif-avatar {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
}

.notif-avatar svg {
  border-radius: 8px;
}

.notif-body {
  flex: 1;
  min-width: 0;
}

.notif-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 2px;
}

.notif-provider-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

/* 已读通知标题变淡 */
.notif-card:not(.unread) .notif-provider-name {
  font-weight: 400;
  color: var(--text-secondary);
}

.notif-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-accent);
  flex-shrink: 0;
}

.notif-time {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-left: auto;
  white-space: nowrap;
}

.notif-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.4;
  overflow: hidden;
  white-space: nowrap;
}

/* 通知描述文本：默认不滚动 */
.notif-desc-text {
  display: inline-block;
  /* 默认滚动距离为 0，由 JS 动态设置 */
  --marquee-distance: 0px;
}

/* 文本溢出时由 JS 添加 marquee class 触发滚动 */
.notif-desc-text.marquee {
  animation: notif-marquee 12s linear infinite;
}

/* marquee 动画：开头停顿2秒 → 滚动 → 末尾停顿2秒 → 循环
 * 滚动距离使用 CSS 变量 --marquee-distance（像素值，由 JS 检测溢出后设置）
 * 这样可以精确表达"文字宽度-容器宽度"的位移 */
@keyframes notif-marquee {
  0%, 15% { transform: translateX(0); }  /* 开头停顿约2秒 */
  85%, 100% { transform: translateX(calc(-1 * var(--marquee-distance))); }  /* 滚动到末尾后停顿 */
}

/* 空状态 */
.drawer-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  font-size: 14px;
}

/* 右侧滑出动画 */
.notif-drawer-enter-active { animation: drawerSlideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
.notif-drawer-leave-active { animation: drawerSlideOut 0.2s cubic-bezier(0.4, 0, 1, 1); }

@keyframes drawerSlideIn {
  from {
  transform: translateX(100%);
  opacity: 0.5;
  }
  to {
  transform: translateX(0);
  opacity: 1;
  }
}

@keyframes drawerSlideOut {
  from {
  transform: translateX(0);
  opacity: 1;
  }
  to {
  transform: translateX(100%);
  opacity: 0;
  }
}

/* 移动端适配 */
@media (max-width: 768px) {
  .sidebar { display: none; }
  .bottom-bar { display: flex; }
  .topbar-title { display: none; }
  .mobile-brand { display: flex; }
  #flymail-app { flex-direction: column; }
  .main-wrapper { height: calc(100vh - var(--bottom-bar-height)); }
  .topbar { padding: 0 var(--space-4); }
  .content { padding-bottom: var(--bottom-bar-height); }
  .notification-drawer {
  width: 100%;
  }
}
</style>
