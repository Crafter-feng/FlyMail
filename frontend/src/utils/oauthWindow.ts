/**
 * OAuth 授权窗口工具
 *
 * 飞牛 OS 手机 App 内嵌 WebView 特点：
 * 1. await 之后再 window.open → 常被静默拦截（返回 null，界面「没反应」）
 * 2. 必须在用户点击的同步调用栈里先 open about:blank，拿到链接后再 location.href 跳转
 * 3. 不要对已导航到 Google/微软 的窗口 document.write（跨域会抛错，后续跳转中断）
 * 4. Google 对部分 WebView UA 更严格，微软相对宽松——故 Gmail 更容易在 App 内失败
 */

export type OpenAuthWindowResult = {
  /** 预打开的窗口；null 表示被环境拦截 */
  win: Window | null;
  /** 是否疑似移动端 / App 内 WebView */
  isMobileLike: boolean;
};

/** 是否手机或常见 App 内置浏览器 */
export function isMobileLikeUa(ua = navigator.userAgent): boolean {
  return /Android|iPhone|iPad|iPod|Mobile|FNOS|fnOS|FlyNas|WebView/i.test(ua);
}

/**
 * 在用户点击的同步阶段预开授权窗口（务必在任何 await 之前调用）。
 */
export function openAuthWindowSync(providerLabel: string): OpenAuthWindowResult {
  const isMobileLike = isMobileLikeUa();
  // 移动端不要带 width/height，部分 WebView 会当成「弹窗」直接拦掉
  const win = isMobileLike
    ? window.open('about:blank', '_blank')
    : window.open('about:blank', '_blank', 'width=600,height=700,scrollbars=yes,resizable=yes');

  if (win) {
    try {
      const safe = escapeHtml(providerLabel);
      win.document.write(
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"/>' +
          '<meta name="viewport" content="width=device-width,initial-scale=1"/>' +
          '<title>正在跳转...</title>' +
          '<style>body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;background:#f5f5f7;color:#1d1d1f;padding:24px;text-align:center;line-height:1.5}' +
          'p{margin:0;font-size:15px}</style></head><body><p>正在跳转到 ' +
          safe +
          ' 授权页面...</p></body></html>',
      );
      win.document.close();
    } catch {
      // 忽略占位页写入失败
    }
  }

  return { win, isMobileLike };
}

/** 将预开窗口导航到 OAuth URL；失败时关闭占位窗 */
export function navigateAuthWindow(win: Window | null, authUrl: string): boolean {
  if (!win || win.closed) return false;
  try {
    win.location.href = authUrl;
    return true;
  } catch {
    try {
      win.close();
    } catch {
      /* ignore */
    }
    return false;
  }
}

export function closeAuthWindow(win: Window | null) {
  if (!win || win.closed) return;
  try {
    win.close();
  } catch {
    /* ignore */
  }
}

/** 弹窗被拦截时的提示文案 */
export function authWindowBlockedMessage(providerLabel: string): string {
  return (
    '无法打开 ' +
    providerLabel +
    ' 授权窗口。飞牛 App 内置浏览器常会拦截授权页（Google 更严格）。' +
    '请用系统 Safari / Chrome 打开飞邮后再点重新授权；或在电脑网页端完成授权。'
  );
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
