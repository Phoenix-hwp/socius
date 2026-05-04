// AI Model Shim - Universal Proxy for Kimi K2.6 and DeepSeek V4 Pro
//
// 支持通过环境变量切换目标 API：
//   - Moonshot (Kimi K2.6): https://api.moonshot.ai/v1
//   - DeepSeek (V4 Pro): https://api.deepseek.com
//
// 核心功能：为思考模型注入缺失的 reasoning_content 字段
// 解决错误："thinking is enabled but reasoning_content is missing"

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { request } from 'undici';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ==================== 加载配置文件 ====================
function loadConfig() {
  const configPath = path.join(__dirname, 'config.json');
  try {
    const raw = fs.readFileSync(configPath, 'utf8');
    return JSON.parse(raw);
  } catch (err) {
    console.error('[WARNING] config.json 未找到或解析失败:', err.message);
    console.error('[INFO] 将使用环境变量作为备用配置');
    return null;
  }
}

const config = loadConfig();

// ==================== 配置区域 ====================
const PORT = parseInt(process.env.SHIM_PORT || (config?.shim?.port || '8787'), 10);
const HOST = process.env.SHIM_HOST || (config?.shim?.host || '127.0.0.1');
const DEBUG = process.env.SHIM_DEBUG === '1' || config?.shim?.debug === true;

// 目标 API 地址（通过环境变量切换，或从 config.json 读取）
const TARGET = (process.env.SHIM_TARGET || '').replace(/\/+$/, '');

// 模型检测关键词
const THINKING_MODELS = ['kimi-k2.6', 'deepseek-v4-pro', 'deepseek-v4-r1', 'deepseek-reasoner'];

// 需要过滤图片的模型（DeepSeek 不支持 image_url）
const IMAGE_FILTER_MODELS = ['deepseek'];  // 匹配 deepseek-v4-pro 等

// 代理设置
const PLACEHOLDER = ' ';  // 最小占位符，满足 API 验证
const UPSTREAM_RETRIES = Math.max(0, parseInt(process.env.SHIM_UPSTREAM_RETRIES || '2', 10));
const RETRY_BASE_MS = Math.max(50, parseInt(process.env.SHIM_RETRY_BASE_MS || '250', 10));
const KEEPALIVE_INTERVAL_MS = Math.max(0, parseInt(process.env.SHIM_KEEPALIVE_MS || '15000', 10));
const TCP_KEEPALIVE_MS = Math.max(0, parseInt(process.env.SHIM_TCP_KEEPALIVE_MS || '15000', 10));

// 日志设置
const LOG_PATH = process.env.SHIM_LOG || path.join(__dirname, 'ai-model-shim.log');
const LOG_MAX_BYTES = 5 * 1024 * 1024;

// ==================== 日志功能 ====================
function rotateIfBig() {
  try {
    const st = fs.statSync(LOG_PATH);
    if (st.size > LOG_MAX_BYTES) {
      const rotated = LOG_PATH + '.1';
      try { fs.unlinkSync(rotated); } catch {}
      fs.renameSync(LOG_PATH, rotated);
    }
  } catch {}
}
rotateIfBig();

const logStream = fs.createWriteStream(LOG_PATH, { flags: 'a' });
logStream.on('error', (err) => {
  console.error(new Date().toISOString(), 'LOG STREAM ERROR', err.message);
});

function ts() { return new Date().toISOString(); }

function log(...args) {
  const line = `${ts()} ${args.map((a) => (typeof a === 'string' ? a : JSON.stringify(a))).join(' ')}\n`;
  process.stdout.write(line);
  try { logStream.write(line); } catch {}
}

function dlog(...args) { if (DEBUG) log('[debug]', ...args); }

// 统计信息
const stats = { req: 0, err: 0, patched: 0, byStatus: Object.create(null), windowStart: Date.now() };
function bumpStatus(code) {
  const k = String(code);
  stats.byStatus[k] = (stats.byStatus[k] || 0) + 1;
}

setInterval(() => {
  const elapsed = ((Date.now() - stats.windowStart) / 1000).toFixed(0);
  const statusStr = Object.entries(stats.byStatus).sort((a, b) => Number(a[0]) - Number(b[0])).map(([k, v]) => `${k}=${v}`).join(',') || '-';
  log(`[summary] window=${elapsed}s req=${stats.req} err=${stats.err} patched=${stats.patched} statuses=${statusStr}`);
  stats.req = 0; stats.err = 0; stats.patched = 0; stats.byStatus = Object.create(null); stats.windowStart = Date.now();
}, 60_000).unref();

// ==================== 核心修复逻辑 ====================

/**
 * 检测是否为思考模型
 * @param {string} model - 模型名称
 * @returns {boolean}
 */
function isThinkingModel(model) {
  if (!model) return false;
  const lowerModel = model.toLowerCase();
  return THINKING_MODELS.some(m => lowerModel.includes(m));
}

/**
 * 检测是否需要 reasoning_content 修复
 * @param {string} targetUrl - 目标 API URL
 * @param {string} model - 模型名称
 * @returns {boolean}
 */
function needsReasoningPatch(targetUrl, model) {
  // Moonshot API 总是需要修复（如果模型是思考模型）
  if (targetUrl.includes('moonshot')) return true;
  // DeepSeek API 仅在思考模式下需要修复
  if (targetUrl.includes('deepseek')) return isThinkingModel(model);
  return false;
}

/**
 * 修复消息数组中的 reasoning_content
 * @param {object} body - 请求体
 * @param {string} targetUrl - 目标 API
 * @returns {number} 修复的消息数量
 */
function patchMessagesForThinkingModels(body, targetUrl) {
  if (!body || !Array.isArray(body.messages)) return 0;

  const model = body.model || '';
  if (!needsReasoningPatch(targetUrl, model)) return 0;

  let patched = 0;
  for (const msg of body.messages) {
    if (!msg || msg.role !== 'assistant') continue;
    if (!Array.isArray(msg.tool_calls) || msg.tool_calls.length === 0) continue;

    const rc = msg.reasoning_content;
    if (typeof rc !== 'string' || rc.trim() === '') {
      msg.reasoning_content = PLACEHOLDER;
      patched++;
      dlog(`patched reasoning_content for model=${model}, msg_index=${patched}`);
    }
  }
  return patched;
}

/**
 * 过滤消息中的图片内容（DeepSeek 不支持 image_url）
 * @param {object} body - 请求体
 * @param {string} targetUrl - 目标 API
 * @returns {number} 过滤的消息数量
 */
function filterImageContent(body, targetUrl) {
  if (!body || !Array.isArray(body.messages)) return 0;
  if (!targetUrl.includes('deepseek')) return 0; // 只对 DeepSeek 启用

  let filtered = 0;
  for (const msg of body.messages) {
    if (!msg || !msg.content) continue;

    // 处理 array 类型的 content（包含图片）
    if (Array.isArray(msg.content)) {
      const textParts = [];
      for (const part of msg.content) {
        if (part.type === 'text' && part.text) {
          textParts.push(part.text);
        } else if (part.type === 'image_url') {
          // 跳过图片，记录日志
          dlog(`filtered image_url from message, role=${msg.role}`);
          filtered++;
        }
      }
      // 将数组转换为纯文本
      if (textParts.length > 0) {
        msg.content = textParts.join('\n');
      } else {
        msg.content = '[图片内容已过滤]';
      }
    }
  }
  return filtered;
}

// ==================== HTTP 工具函数 ====================
function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', (c) => chunks.push(c));
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

const HOP_BY_HOP = new Set(['connection','keep-alive','proxy-authenticate','proxy-authorization','te','trailers','transfer-encoding','upgrade','host','content-length']);
function copyHeaders(src) {
  const out = {};
  for (const [k, v] of Object.entries(src)) {
    if (HOP_BY_HOP.has(k.toLowerCase())) continue;
    out[k] = v;
  }
  return out;
}

function sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }

function isRetryableUpstreamError(err) {
  if (!err) return false;
  const code = String(err.code || '');
  const msg = String(err.message || '');
  if (code === 'ECONNRESET' || code === 'ETIMEDOUT') return true;
  if (msg.includes('ECONNRESET') || msg.includes('ETIMEDOUT')) return true;
  if (msg.includes('UND_ERR_SOCKET') || msg.includes('UND_ERR_CONNECT_TIMEOUT') || msg.includes('UND_ERR_HEADERS_TIMEOUT')) return true;
  return false;
}

async function requestWithRetry(url, options, reqMeta) {
  let attempt = 0;
  while (true) {
    try {
      return await request(url, options);
    } catch (err) {
      const canRetry = isRetryableUpstreamError(err) && attempt < UPSTREAM_RETRIES;
      if (!canRetry) throw err;
      const waitMs = RETRY_BASE_MS * (attempt + 1);
      log('UPSTREAM RETRY', `attempt=${attempt + 1}/${UPSTREAM_RETRIES}`, reqMeta, String(err.code || ''), err.message, `wait=${waitMs}ms`);
      await sleep(waitMs);
      attempt++;
    }
  }
}

function safeWrite(res, chunk) {
  if (!res || res.destroyed || res.writableEnded) return false;
  try { return res.write(chunk); } catch (err) { log('RES WRITE ERROR', err.message); return false; }
}

function safeEnd(res) {
  if (!res || res.destroyed || res.writableEnded) return;
  try { res.end(); } catch (err) { log('RES END ERROR', err.message); }
}

// ==================== HTTP 服务器 ====================
const server = http.createServer(async (req, res) => {
  const started = Date.now();
  stats.req++;
  res.on('error', (err) => { log('RES ERROR', err.code || '', err.message); });
  req.on('error', (err) => { log('REQ ERROR', err.code || '', err.message); });

  let url;
  try {
    url = new URL(req.url, `http://${req.headers.host || HOST + ':' + PORT}`);
  } catch (e) {
    safeWrite(res, '');
    res.writeHead(400, { 'content-type': 'text/plain' });
    safeEnd(res);
    return;
  }

  // 健康检查端点
  if (url.pathname === '/healthz' || url.pathname === '/_shim/healthz') {
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify({
      ok: true,
      uptimeSec: Math.round(process.uptime()),
      target: TARGET,
      pid: process.pid,
      model: process.env.CURRENT_MODEL || 'unknown'
    }));
    return;
  }

  // 模型信息端点
  if (url.pathname === '/_shim/model') {
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify({
      current: process.env.CURRENT_MODEL || 'not_set',
      target: TARGET,
      supported: THINKING_MODELS,
      thinkingPatchEnabled: true
    }));
    return;
  }

  // 构建上游 URL
  let upstreamPath = url.pathname;
  if (upstreamPath.startsWith('/v1/')) upstreamPath = upstreamPath.slice(3);
  else if (upstreamPath === '/v1') upstreamPath = '';
  const upstreamUrl = TARGET + upstreamPath + url.search;

  // 读取请求体
  let raw;
  try { raw = await readBody(req); } catch (err) {
    stats.err++;
    log('REQ READ ERROR', err.message);
    try { res.writeHead(400, { 'content-type': 'text/plain' }); res.end('shim: failed to read request body: ' + err.message); } catch {}
    return;
  }

  // 修复 reasoning_content 和过滤图片
  let bodyToSend = raw.length > 0 ? raw : undefined;
  let patchInfo = '';
  if (req.method === 'POST' && raw.length > 0) {
    let json = null;
    try { json = JSON.parse(raw.toString('utf8')); } catch {}
    if (json && Array.isArray(json.messages)) {
      // 1. 修复 reasoning_content
      const n = patchMessagesForThinkingModels(json, TARGET);
      stats.patched += n;
      // 2. 过滤图片内容（DeepSeek 不支持）
      const imgFiltered = filterImageContent(json, TARGET);
      if (imgFiltered > 0) {
        log(`filtered ${imgFiltered} image(s) for DeepSeek model`);
      }
      try { bodyToSend = Buffer.from(JSON.stringify(json), 'utf8'); } catch (err) { log('JSON STRINGIFY ERROR', err.message); bodyToSend = raw; }
      patchInfo = ` model=${json.model || '?'} msgs=${json.messages.length} patched=${n} filtered=${imgFiltered} stream=${!!json.stream}`;
      if (DEBUG && n > 0) dlog(`patched ${n} assistant.tool_calls message(s) for ${TARGET}`);
    }
  }

  // 转发到上游
  const upstreamHeaders = copyHeaders(req.headers);
  if (bodyToSend) upstreamHeaders['content-length'] = String(bodyToSend.length);

  let upstream;
  try {
    upstream = await requestWithRetry(upstreamUrl, { method: req.method, headers: upstreamHeaders, body: bodyToSend, maxRedirections: 0 }, `${req.method} ${upstreamUrl}`);
  } catch (err) {
    stats.err++;
    bumpStatus(502);
    log('UPSTREAM ERROR', req.method, upstreamUrl, err.message);
    try { res.writeHead(502, { 'content-type': 'application/json' }); res.end(JSON.stringify({ error: { message: 'shim: upstream connect error: ' + err.message, type: 'shim_upstream_error' } })); } catch {}
    return;
  }

  // 处理响应
  bumpStatus(upstream.statusCode);
  const respHeaders = copyHeaders(upstream.headers);
  const ct = String(upstream.headers['content-type'] || '');
  const isSSE = ct.includes('text/event-stream');
  if (isSSE) {
    respHeaders['x-accel-buffering'] = 'no';
    respHeaders['cache-control'] = 'no-cache, no-transform';
  }
  try { res.writeHead(upstream.statusCode, respHeaders); } catch (err) {
    log('RES WRITEHEAD ERROR', err.message);
    try { upstream.body.destroy(); } catch {}
    return;
  }

  // TCP Keepalive
  if (isSSE && TCP_KEEPALIVE_MS > 0) {
    try {
      const sock = res.socket || req.socket;
      if (sock && typeof sock.setKeepAlive === 'function') {
        sock.setKeepAlive(true, TCP_KEEPALIVE_MS);
        if (typeof sock.setNoDelay === 'function') sock.setNoDelay(true);
      }
    } catch (err) { log('TCP KEEPALIVE SET ERROR', err.message); }
  }

  // SSE Keepalive
  let lastWriteAt = Date.now();
  let keepAliveTimer = null;
  let keepAliveCount = 0;
  function stopKeepAlive() { if (keepAliveTimer) { clearInterval(keepAliveTimer); keepAliveTimer = null; } }

  if (isSSE && KEEPALIVE_INTERVAL_MS > 0) {
    const tick = Math.max(1000, Math.floor(KEEPALIVE_INTERVAL_MS / 2));
    keepAliveTimer = setInterval(() => {
      if (!res || res.destroyed || res.writableEnded) { stopKeepAlive(); return; }
      if (Date.now() - lastWriteAt >= KEEPALIVE_INTERVAL_MS) {
        if (safeWrite(res, ': keepalive\n\n')) { lastWriteAt = Date.now(); keepAliveCount++; }
      }
    }, tick);
    keepAliveTimer.unref();
  }

  // 数据传输
  upstream.body.on('data', (c) => { if (safeWrite(res, c)) lastWriteAt = Date.now(); });
  upstream.body.on('end', () => {
    stopKeepAlive(); safeEnd(res);
    const ms = Date.now() - started;
    const ka = isSSE && keepAliveCount > 0 ? ` keepalive=${keepAliveCount}` : '';
    log(`${req.method} ${url.pathname} -> ${upstream.statusCode} ${ms}ms${patchInfo}${ka}`);
  });
  upstream.body.on('error', (err) => { stats.err++; stopKeepAlive(); log('UPSTREAM BODY ERROR', err.message); safeEnd(res); });
  req.on('close', () => { stopKeepAlive(); if (!res.writableEnded) { try { upstream.body.destroy(); } catch {} } });
});

// ==================== 错误处理和启动 ====================
server.on('clientError', (err, socket) => { log('CLIENT ERROR', err.code || '', err.message); try { socket.destroy(); } catch {} });
server.on('error', (err) => { log('SERVER ERROR', err.code || '', err.message); });

process.on('uncaughtException', (err) => { log('UNCAUGHT EXCEPTION', err && err.stack ? err.stack : String(err)); });
process.on('unhandledRejection', (reason) => { const s = reason && reason.stack ? reason.stack : String(reason); log('UNHANDLED REJECTION', s); });

server.requestTimeout = 0;
server.keepAliveTimeout = 600_000;
server.headersTimeout = 605_000;
server.timeout = 0;

server.listen(PORT, HOST, () => {
  log(`=============================================`);
  log(`AI Model Shim 启动成功`);
  log(`监听地址: http://${HOST}:${PORT}`);
  log(`目标 API: ${TARGET}`);
  log(`当前模型: ${process.env.CURRENT_MODEL || '未设置'}`);
  log(`支持模型: ${THINKING_MODELS.join(', ')}`);
  log(`日志文件: ${LOG_PATH}`);
  log(`=============================================`);
  log(`健康检查: http://${HOST}:${PORT}/healthz`);
  log(`模型信息: http://${HOST}:${PORT}/_shim/model`);
  log(`=============================================`);
});

function shutdown(sig) {
  log(`received ${sig}, shutting down`);
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(0), 2000).unref();
}
process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));
