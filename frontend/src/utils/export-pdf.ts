/**
 * 邮件导出 PDF 工具
 *
 * ★ 方案变更历史
 * 1. html2pdf.js（html2canvas + jsPDF）→ 连续4种容器隐藏方式都空白
 *    原因：html2canvas 在飞牛OS WebView 中不兼容，无法正确截图
 * 2. iframe + window.print() → 当前方案
 *    优势：零依赖、矢量 PDF（文字可选可搜）、浏览器原生功能
 *
 * 原理：创建隐藏 iframe，在 iframe 中渲染邮件 HTML，调用 print()
 * 用户在打印对话框中选择"保存为 PDF"即可导出
 *
 * 排版结构（所见即所得）：
 * ┌─────────────────────────────┐
 * │  主题（大标题）              │
 * │  ─────────────────────────  │
 * │  发件人：xxx <xxx@qq.com>    │
 * │  收件人：xxx, xxx            │
 * │  抄  送：xxx, xxx            │
 * │  日  期：2026-07-12 10:30    │
 * │  ─────────────────────────  │
 * │                              │
 * │  邮件正文（保留原始HTML格式） │
 * │  ...                         │
 * │                              │
 * └─────────────────────────────┘
 */
import { sanitizeHtml } from './sanitize'
import { extractName } from './mail-helpers'
import type { Message } from '../types/mail'

/**
 * 导出邮件为 PDF 文件
 *
 * 通过 iframe + window.print() 实现，用户在打印对话框中选择"保存为 PDF"
 *
 * @param msg 邮件对象，需包含 subject、from_addr、body_html 等字段
 */
export async function exportMailToPDF(msg: Message): Promise<void> {
  // 构建邮件头部 HTML（主题 + 元数据表格）
  const headerHtml = buildMailHeader(msg)
  // 获取净化后的正文 HTML，优先 html，缺失时回退到纯文本
  const bodyHtml = sanitizeHtml(msg.body_html) || escapeHtml(msg.body_text || '')

  // 组装完整的 HTML 文档（包含打印样式）
  const fullHtml = buildFullHtml(msg, headerHtml, bodyHtml)

  // 创建隐藏 iframe 作为打印容器
  // 用 iframe 而非 window.open：避免飞牛OS WebView 拦截弹窗
  // iframe 尺寸设为 0 不影响页面，但内部内容仍可正常渲染和打印
  const iframe = document.createElement('iframe')
  iframe.style.cssText = 'position:fixed;top:0;left:0;width:0;height:0;border:0;visibility:hidden;'
  document.body.appendChild(iframe)

  try {
    // 获取 iframe 的 document，写入邮件 HTML
    const doc = iframe.contentDocument || iframe.contentWindow?.document
    if (!doc) {
      throw new Error('无法访问 iframe 文档')
    }

    doc.open()
    doc.write(fullHtml)
    doc.close()

    // 等待浏览器完成布局渲染
    await waitForRender()
    // 等待 iframe 内所有图片加载完成
    await waitForImages(doc.body)

    // 调用 iframe 的 print 方法，触发浏览器打印对话框
    // 用户可在对话框中选择"保存为 PDF"来导出
    iframe.contentWindow?.focus()
    iframe.contentWindow?.print()
  } finally {
    // 延迟移除 iframe：打印对话框是同步阻塞的，关闭后才执行 finally
    // 但某些环境下 print() 是异步的，延迟 1 秒移除确保安全
    setTimeout(() => {
      if (iframe.parentNode) {
        document.body.removeChild(iframe)
      }
    }, 1000)
  }
}

/**
 * 构建完整的 HTML 文档（含打印样式）
 *
 * 独立的 HTML 文档，不受主页面 CSS 影响，保证打印效果
 */
function buildFullHtml(msg: Message, headerHtml: string, bodyHtml: string): string {
  const title = escapeHtml(msg.subject || '邮件导出')
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title}</title>
  <style>
    /* 打印样式：A4 纸张，10mm 边距 */
    @page {
      size: A4 portrait;
      margin: 10mm;
    }
    /* 基础排版 */
    body {
      font-family: -apple-system, 'Segoe UI', 'Microsoft YaHei', 'PingFang SC', sans-serif;
      color: #333;
      line-height: 1.6;
      padding: 20px;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }
    /* 邮件主题 */
    h1.mail-subject {
      font-size: 20px;
      font-weight: 600;
      margin: 0 0 12px 0;
      color: #1a1a1a;
      word-break: break-word;
    }
    /* 元数据表格 */
    table.mail-meta {
      font-size: 12px;
      color: #666;
      line-height: 1.8;
      border-collapse: collapse;
      width: 100%;
    }
    table.mail-meta td {
      vertical-align: top;
      padding-right: 8px;
    }
    table.mail-meta td.label {
      color: #999;
      white-space: nowrap;
      width: 60px;
    }
    table.mail-meta td.value {
      word-break: break-all;
    }
    /* 分隔线 */
    hr.mail-divider {
      border: none;
      border-top: 1px solid #ddd;
      margin: 16px 0;
    }
    /* 邮件正文 */
    .mail-body {
      font-size: 14px;
      line-height: 1.8;
    }
    .mail-body img {
      max-width: 100%;
      height: auto;
    }
    .mail-body table {
      max-width: 100%;
    }
    /* 打印时优化 */
    @media print {
      body { padding: 0; }
    }
  </style>
</head>
<body>
  ${headerHtml}
  <hr class="mail-divider">
  <div class="mail-body">${bodyHtml}</div>
</body>
</html>`
}

/**
 * 构建邮件头部信息 HTML
 *
 * 包含主题（大标题）和元数据表格（发件人/收件人/抄送/日期）
 */
function buildMailHeader(msg: Message): string {
  const fromName = extractName(msg.from_addr)
  const fromEmail = msg.from_addr || ''
  // 发件人显示：名称 + <邮箱>（若名称和邮箱相同则只显示一个）
  const fromDisplay = fromEmail !== fromName
    ? `${escapeHtml(fromName)} &lt;${escapeHtml(fromEmail)}&gt;`
    : escapeHtml(fromName)

  const toDate = msg.to_addr || ''
  const cc = msg.cc || ''
  const date = msg.date || ''

  // 构建元数据行（跳过空字段）
  const metaRows = [
    metaRow('发件人', fromDisplay),
    toDate ? metaRow('收件人', escapeHtml(toDate)) : '',
    cc ? metaRow('抄  送', escapeHtml(cc)) : '',
    date ? metaRow('日  期', escapeHtml(date)) : '',
  ].filter(Boolean).join('')

  return `
    <h1 class="mail-subject">${escapeHtml(msg.subject || '(无主题)')}</h1>
    <table class="mail-meta">
      ${metaRows}
    </table>
  `
}

/**
 * 生成元数据表格行
 */
function metaRow(label: string, value: string): string {
  return `<tr><td class="label">${label}</td><td class="value">${value}</td></tr>`
}

/**
 * 等待浏览器完成布局渲染
 *
 * 连续两帧 requestAnimationFrame，确保重排重绘完成
 */
function waitForRender(): Promise<void> {
  return new Promise(resolve => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => resolve())
    })
  })
}

/**
 * 等待容器内所有图片加载完成
 *
 * 打印时如果图片还没加载完，打印结果中图片位置会是空白
 * 遍历所有 img 标签，等待 load/error，超时 5 秒强制继续
 */
function waitForImages(container: HTMLElement | null): Promise<void> {
  if (!container) return Promise.resolve()
  const images = Array.from(container.querySelectorAll('img'))
  if (images.length === 0) return Promise.resolve()

  return new Promise(resolve => {
    let remaining = images.length
    const timer = setTimeout(() => {
      console.warn('[export-pdf] 图片加载超时，强制继续')
      resolve()
    }, 5000)

    const onDone = () => {
      remaining--
      if (remaining <= 0) {
        clearTimeout(timer)
        resolve()
      }
    }

    images.forEach(img => {
      if (img.complete) {
        onDone()
      } else {
        img.addEventListener('load', onDone, { once: true })
        img.addEventListener('error', onDone, { once: true })
      }
    })
  })
}

/**
 * HTML 转义
 *
 * 防止邮件头部信息中的特殊字符（< > & "）破坏 HTML 结构
 */
function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}
