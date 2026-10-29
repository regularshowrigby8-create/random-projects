# Deploying this repo

The deployment layer lives **in the repository** — no Vercel project, no hidden
platform config. There are two ways to run it: the built-in Node host (works
anywhere, including Docker and any Vercel alternative), or a one-command push
to a third-party static host.

```
server.js            sta1610/server.js   → dependency-free static host (the deploy target)
package.json         npm start / deploy:netlify / deploy:cloudflare / deploy:surge
netlify.toml         Netlify    — publish dir + headers + SPA fallback
wrangler.toml        Cloudflare Pages — build output dir
render.yaml          Render     — web service + health check
Dockerfile           any container host (Fly, Railway, a VPS, Kubernetes)
```

## 1. Built-in host (default, zero dependencies)

```bash
npm start                      # http://localhost:8080
PORT=3000 npm start            # custom port
curl -s localhost:8080/healthz # liveness + build info
```

`sta1610/server.js` serves the whole site (it is a single `index.html`) with:

* gzip on the fly (~388 KB → ~94 KB) and an in-memory cache
* strong `ETag` + `Last-Modified` → `304 Not Modified` on revisits
* `Cache-Control: no-cache` for HTML, immutable for hashed assets
* path-traversal protection, `405` for non-GET, `/healthz` for uptime checks
* binds `HOST=0.0.0.0` so it works behind any proxy or preview URL
* graceful `SIGTERM` shutdown

This is what runs when you open the live preview — it is deployed straight from
the repo.

## 2. Vercel alternatives

Pick any; each reads config that is already committed.

| Host | Command / action | Reads |
| --- | --- | --- |
| Netlify | `npm run deploy:netlify` (after `npx netlify-cli login`), or import the repo in the Netlify UI / use the *Deploy to Netlify* button | `netlify.toml` |
| Cloudflare Pages | `npm run deploy:cloudflare` (after `npx wrangler login`), or connect the repo with output dir `sta1610` | `wrangler.toml` |
| Render | New → Blueprint → select this repo | `render.yaml` |
| Fly.io | `fly launch` then `fly deploy` | `Dockerfile` |
| Railway / any VPS | deploy the `Dockerfile`, or `npm start` behind nginx/Caddy | `Dockerfile` |
| Surge (simplest) | `npm run deploy:surge` | `package.json` |

Netlify one-click import URL for this repository:

```
https://app.netlify.com/start/deploy?repository=https://github.com/regularshowrigby8-create/random-projects
```

No build step is required anywhere — publish directory is `sta1610` and there
is nothing to install.

## 3. Docker

```bash
docker build -t sta1610 .
docker run -p 8080:8080 sta1610
```

## Notes

* `sta1610/index.html` is self-contained apart from the Google Fonts and KaTeX
  CDN stylesheets/scripts, so it also works as a plain file.
* Deploying to Netlify/Cloudflare/Render/Fly needs credentials and outbound
  access to those APIs. The build environment used to author this repo only
  reaches GitHub and the npm/PyPI registries, so the deploy there is done with
  the built-in host (option 1). Running any command in option 2 from your own
  machine or CI publishes the identical files.
