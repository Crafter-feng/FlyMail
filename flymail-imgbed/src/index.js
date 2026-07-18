/**
 * 飞邮通知图床 Worker
 *
 * 接口：
 *   GET  /health          探活
 *   POST /upload          上传图片（Bearer Token）
 *   GET  /i/:key          公开读图（供 Bark 拉取）
 *   POST /purge           清理全部图片（Bearer Token）
 *   DELETE /i/:key        删除单张（Bearer Token）
 *
 * 鉴权：Authorization: Bearer <UPLOAD_TOKEN>
 * 存储：R2 binding IMAGES
 */

const DEFAULT_MAX_BYTES = 1.5 * 1024 * 1024;

export default {
  async fetch(request, env, ctx) {
    try {
      return await handle(request, env);
    } catch (err) {
      return json({ ok: false, error: String(err && err.message ? err.message : err) }, 500);
    }
  },
};

async function handle(request, env) {
  const url = new URL(request.url);
  const path = url.pathname.replace(/\/+$/, "") || "/";
  const method = request.method.toUpperCase();

  if (method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders() });
  }

  if (method === "GET" && (path === "/" || path === "/health")) {
    return json({
      ok: true,
      service: "flymail-imgbed",
      version: "1.0.0",
    });
  }

  if (method === "GET" && path.startsWith("/i/")) {
    const key = decodeURIComponent(path.slice(3));
    if (!key || key.includes("..") || key.includes("\\")) {
      return json({ ok: false, error: "invalid key" }, 400);
    }
    const obj = await env.IMAGES.get(key);
    if (!obj) {
      return json({ ok: false, error: "not found" }, 404);
    }
    const headers = new Headers();
    obj.writeHttpMetadata(headers);
    headers.set("etag", obj.httpEtag);
    headers.set("cache-control", "public, max-age=86400");
    headers.set("access-control-allow-origin", "*");
    if (!headers.get("content-type")) {
      headers.set("content-type", guessContentType(key));
    }
    return new Response(obj.body, { headers });
  }

  const authErr = assertAuth(request, env);
  if (authErr) return authErr;

  if (method === "POST" && path === "/upload") {
    return await handleUpload(request, env, url);
  }

  if (method === "POST" && path === "/purge") {
    return await handlePurge(env);
  }

  if (method === "DELETE" && path.startsWith("/i/")) {
    const key = decodeURIComponent(path.slice(3));
    if (!key) return json({ ok: false, error: "invalid key" }, 400);
    await env.IMAGES.delete(key);
    return json({ ok: true, deleted: key });
  }

  return json({ ok: false, error: "not found" }, 404);
}

function assertAuth(request, env) {
  const token = (env.UPLOAD_TOKEN || "").trim();
  if (!token) {
    return json({
      ok: false,
      error: "服务端未配置 UPLOAD_TOKEN，请在 Cloudflare 中设置 Secret",
    }, 500);
  }
  const header = request.headers.get("Authorization") || "";
  const m = header.match(/^Bearer\s+(.+)$/i);
  const got = m ? m[1].trim() : "";
  if (!got || got !== token) {
    return json({ ok: false, error: "unauthorized" }, 401);
  }
  return null;
}

async function handleUpload(request, env, url) {
  const maxBytes = Number(env.MAX_BYTES) > 0 ? Number(env.MAX_BYTES) : DEFAULT_MAX_BYTES;
  const ct = (request.headers.get("content-type") || "").toLowerCase();

  let bytes;
  let contentType = "image/png";
  let ext = "png";

  if (ct.includes("multipart/form-data")) {
    const form = await request.formData();
    const file = form.get("file") || form.get("image") || form.get("photo");
    if (!file || typeof file.arrayBuffer !== "function") {
      return json({ ok: false, error: "multipart 需字段 file/image/photo" }, 400);
    }
    bytes = new Uint8Array(await file.arrayBuffer());
    const fct = (file.type || "").toLowerCase();
    if (fct.includes("jpeg") || fct.includes("jpg")) {
      contentType = "image/jpeg";
      ext = "jpg";
    } else if (fct.includes("png") || !fct) {
      contentType = "image/png";
      ext = "png";
    } else {
      return json({ ok: false, error: "仅支持 image/png 或 image/jpeg" }, 400);
    }
  } else {
    if (ct.includes("jpeg") || ct.includes("jpg")) {
      contentType = "image/jpeg";
      ext = "jpg";
    } else if (ct && !ct.includes("png") && !ct.includes("octet-stream")) {
      return json({ ok: false, error: "仅支持 image/png 或 image/jpeg" }, 400);
    }
    bytes = new Uint8Array(await request.arrayBuffer());
  }

  if (!bytes || bytes.byteLength === 0) {
    return json({ ok: false, error: "empty body" }, 400);
  }
  if (bytes.byteLength > maxBytes) {
    return json({
      ok: false,
      error: "文件过大，上限 " + Math.floor(maxBytes) + " 字节",
    }, 413);
  }

  if (!looksLikeImage(bytes)) {
    return json({ ok: false, error: "内容不是有效的 PNG/JPEG" }, 400);
  }

  const key = Date.now().toString(36) + "_" + crypto.randomUUID().replace(/-/g, "").slice(0, 16) + "." + ext;
  await env.IMAGES.put(key, bytes, {
    httpMetadata: { contentType },
    customMetadata: { created_at: new Date().toISOString() },
  });

  const publicUrl = url.origin + "/i/" + key;
  return json({
    ok: true,
    url: publicUrl,
    key,
    bytes: bytes.byteLength,
    content_type: contentType,
  });
}

async function handlePurge(env) {
  let deleted = 0;
  let cursor;
  do {
    const listed = await env.IMAGES.list({ cursor, limit: 1000 });
    const keys = (listed.objects || []).map((o) => o.key);
    if (keys.length) {
      await Promise.all(keys.map((k) => env.IMAGES.delete(k)));
      deleted += keys.length;
    }
    cursor = listed.truncated ? listed.cursor : undefined;
  } while (cursor);

  return json({ ok: true, deleted });
}

function looksLikeImage(bytes) {
  if (bytes.byteLength < 4) return false;
  if (bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47) return true;
  if (bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return true;
  return false;
}

function guessContentType(key) {
  const lower = (key || "").toLowerCase();
  if (lower.endsWith(".jpg") || lower.endsWith(".jpeg")) return "image/jpeg";
  return "image/png";
}

function json(data, status) {
  status = status || 200;
  return new Response(JSON.stringify(data), {
    status,
    headers: Object.assign({ "content-type": "application/json; charset=utf-8" }, corsHeaders()),
  });
}

function corsHeaders() {
  return {
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET, POST, DELETE, OPTIONS",
    "access-control-allow-headers": "Authorization, Content-Type",
  };
}
