#!/usr/bin/env node
/* ==========================================================================
   STA1610 static host — a dependency-free deploy target that lives in the repo.
   Serves ./index.html (the whole site is one file) with gzip, ETags, sensible
   cache policy and a health endpoint. Works on any Node host (Render, Railway,
   Fly, a VPS, Docker) or locally:  npm start
   ========================================================================== */
'use strict';

const http = require('http');
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const crypto = require('crypto');

const ROOT = __dirname;
const PORT = Number(process.env.PORT) || 8080;
const HOST = process.env.HOST || '0.0.0.0';
const STARTED = new Date().toISOString();

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2',
  '.txt': 'text/plain; charset=utf-8',
  '.map': 'application/json; charset=utf-8',
  '.webmanifest': 'application/manifest+json'
};
const COMPRESSIBLE = /^(text\/|application\/(json|manifest)|image\/svg)/;

/* small in-memory cache so repeat requests skip disk + gzip work */
const cache = new Map();

function load(file) {
  const stat = fs.statSync(file);
  const key = file + ':' + stat.mtimeMs + ':' + stat.size;
  const hit = cache.get(key);
  if (hit) return hit;
  const raw = fs.readFileSync(file);
  const entry = {
    raw,
    gzip: COMPRESSIBLE.test(mimeFor(file)) && raw.length > 1024 ? zlib.gzipSync(raw, { level: 9 }) : null,
    etag: '"' + crypto.createHash('sha1').update(raw).digest('base64').slice(0, 20) + '"',
    mtime: stat.mtime.getTime(),
    type: mimeFor(file)
  };
  for (const existing of cache.keys()) if (existing.startsWith(file + ':')) cache.delete(existing);
  cache.set(key, entry);
  return entry;
}

function mimeFor(file) {
  return MIME[path.extname(file).toLowerCase()] || 'application/octet-stream';
}

function resolveTarget(urlPath) {
  let rel;
  try {
    rel = decodeURIComponent(urlPath.split('?')[0]);
  } catch (e) {
    return null;
  }
  if (rel === '/' || rel === '') rel = '/index.html';
  /* the pages use #hash navigation, so unknown paths fall back to the app */
  const candidates = [rel, path.posix.join(rel, 'index.html'), '/index.html'];
  for (const candidate of candidates) {
    const file = path.join(ROOT, path.normalize(candidate));
    if (!file.startsWith(ROOT)) continue; /* no traversal */
    if (fs.existsSync(file) && fs.statSync(file).isFile()) return file;
  }
  return null;
}

function send(res, status, body, headers) {
  res.writeHead(status, Object.assign({
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'strict-origin-when-cross-origin'
    /* deliberately no X-Frame-Options / frame-ancestors: the preview embeds this page */
  }, headers));
  res.end(body);
}

const server = http.createServer((req, res) => {
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    return send(res, 405, 'Method Not Allowed', { 'Content-Type': 'text/plain; charset=utf-8', Allow: 'GET, HEAD' });
  }

  const url = req.url || '/';

  if (url === '/healthz') {
    const html = path.join(ROOT, 'index.html');
    const info = {
      ok: true,
      service: 'sta1610-exam-prep',
      startedAt: STARTED,
      uptimeSeconds: Math.round(process.uptime()),
      node: process.version,
      site: fs.existsSync(html) ? { bytes: fs.statSync(html).size, modified: fs.statSync(html).mtime.toISOString() } : null
    };
    return send(res, 200, JSON.stringify(info, null, 2), {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store'
    });
  }

  const file = resolveTarget(url);
  if (!file) {
    return send(res, 404, 'Not found', { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' });
  }

  let entry;
  try {
    entry = load(file);
  } catch (err) {
    return send(res, 500, 'Read error', { 'Content-Type': 'text/plain; charset=utf-8' });
  }

  const isHtml = path.extname(file).toLowerCase() === '.html';
  const wantsGzip = /\bgzip\b/.test(req.headers['accept-encoding'] || '') && entry.gzip;

  const headers = {
    'Content-Type': entry.type,
    'ETag': entry.etag,
    'Last-Modified': new Date(entry.mtime).toUTCString(),
    'Cache-Control': isHtml ? 'no-cache' : 'public, max-age=31536000, immutable',
    'Vary': 'Accept-Encoding'
  };

  if (req.headers['if-none-match'] === entry.etag) {
    return send(res, 304, undefined, headers);
  }

  if (wantsGzip) {
    headers['Content-Encoding'] = 'gzip';
    headers['Content-Length'] = entry.gzip.length;
    res.writeHead(200, Object.assign({ 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'strict-origin-when-cross-origin' }, headers));
    return res.end(req.method === 'HEAD' ? undefined : entry.gzip);
  }

  headers['Content-Length'] = entry.raw.length;
  res.writeHead(200, Object.assign({ 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'strict-origin-when-cross-origin' }, headers));
  res.end(req.method === 'HEAD' ? undefined : entry.raw);
});

server.listen(PORT, HOST, () => {
  console.log('STA1610 static host listening on http://' + HOST + ':' + PORT);
  console.log('Serving ' + path.join(ROOT, 'index.html'));
});

function shutdown(signal) {
  console.log(signal + ' received, closing server…');
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(0), 3000).unref();
}
process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
