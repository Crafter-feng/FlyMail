<template>
  <div class="about-page">
    <!-- 品牌 + 简介 -->
    <div class="about-card">
      <div class="brand-row">
        <img :src="base + 'icon-full.png'" alt="FlyMail" class="brand-logo" @error="onLogoError" />
        <div class="brand-meta">
          <div class="brand-name-line">
            <span class="brand-name">Fly<span class="accent">Mail</span></span>
            <span class="ver">v{{ version }}</span>
          </div>
          <p class="brand-slogan">专为多邮箱用户打造的自托管邮件客户端</p>
        </div>
      </div>
      <p class="brand-desc">
        统一管理 Gmail、Outlook、腾讯邮箱、网易邮箱、iCloud 等主流平台的邮件数据。
        聚合收件箱让您在一个界面查看所有邮箱的重要邮件，告别频繁切换账号的烦恼。
        支持多账号管理、邮件收发、富文本编辑、附件上传下载、定时发送、草稿箱、个性签名及实时同步等丰富功能，满足日常办公与个人使用需求。
      </p>
    </div>

    <!-- 功能 + 技术栈 -->
    <div class="about-card">
      <div class="pill-row">
        <span class="pill" v-for="f in features" :key="f">
          <span class="pill-dot"></span>{{ f }}
        </span>
      </div>
      <div class="divider"></div>
      <div class="pill-row">
        <span class="pill tech" v-for="t in techs" :key="t">{{ t }}</span>
      </div>
    </div>

    <!-- 支持与反馈 -->
    <div class="about-card">
      <div class="qr-row">
        <div class="qr-item">
          <img :src="base + 'afdian.jpg'" alt="爱发电" class="qr-img" />
          <span class="qr-label">爱发电</span>
        </div>
        <div class="qr-item">
          <img :src="base + 'feedback.jpg'" alt="意见反馈" class="qr-img" />
          <span class="qr-label">意见反馈</span>
        </div>
      </div>
    </div>

    <!-- 底部 -->
    <div class="footer">
      <span>© 2026 cliii-one · GNU GPLv3</span>
    </div>
  </div>
</template>

<script setup lang="ts">
const version = import.meta.env.VITE_APP_VERSION || '0.0.0';
const base = import.meta.env.BASE_URL;

function onLogoError(e: Event) {
  (e.target as HTMLImageElement).style.display = 'none';
}

const features = ['多邮箱聚合', '实时同步', '自托管隐私', '跨平台访问'];
const techs = ['Vue 3', 'TypeScript', 'FastAPI', 'SQLite', 'IMAP', 'WebSocket'];
</script>

<style scoped>
.about-page {
  height: 100%;
  overflow-y: auto;
  padding: var(--space-5) var(--space-6);
  background: var(--bg-secondary);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.about-card {
  background: var(--bg-card);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-card);
  padding: var(--space-4) var(--space-5);
  flex-shrink: 0;
}

/* 品牌区 */
.brand-row {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.brand-logo {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  box-shadow: var(--shadow-sm);
  flex-shrink: 0;
}

.brand-meta {
  flex: 1;
  min-width: 0;
}

.brand-name-line {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}

.brand-name {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
}

.brand-name .accent {
  color: var(--color-accent);
}

.ver {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  font-variant-numeric: tabular-nums;
}

.brand-slogan {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  margin: 3px 0 0;
}

.brand-desc {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.7;
  margin: var(--space-3) 0 0;
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-color);
}

/* 标签行 */
.pill-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 12px;
  background: var(--bg-hover);
  border-radius: var(--border-radius-full);
  font-size: var(--text-xs);
  color: var(--text-secondary);
  font-weight: 500;
}

.pill-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--color-accent);
}

.pill.tech {
  background: var(--bg-secondary);
  color: var(--text-tertiary);
}

.divider {
  height: 1px;
  background: var(--border-color);
  margin: var(--space-3) 0;
}

/* 二维码 */
.qr-row {
  display: flex;
  gap: var(--space-6);
  justify-content: center;
}

.qr-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
}

.qr-img {
  width: 140px;
  height: 140px;
  border-radius: var(--border-radius-md);
  object-fit: cover;
  border: 1px solid var(--border-color);
}

.qr-label {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  font-weight: 500;
}

/* 底部 */
.footer {
  text-align: center;
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  padding: var(--space-2) 0;
  margin-top: auto;
  opacity: 0.7;
}

/* 移动端 */
@media (max-width: 768px) {
  .about-page {
    padding: var(--space-4);
  }

  .about-card {
    padding: var(--space-4);
  }

  .brand-logo {
    width: 40px;
    height: 40px;
    border-radius: 10px;
  }

  .brand-name {
    font-size: 17px;
  }

  .qr-img {
    width: 96px;
    height: 96px;
  }
}
</style>
