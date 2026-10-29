# Deploying this repo

The deployment layer lives **in the repository** — no Vercel project, no hidden
platform config. There are two ways to run it: the built-in Node host (works
anywhere, including Docker and any Vercel alternative), or a one-command push
to a third-party static host.

```
sta1610/server.js     dependency-free static host (the default deploy target)
package.json          start / start:serve / start:sirv / docker:* / deploy:*
Dockerfile            any container host (Fly, Railway, a VPS, Kubernetes)
docker-compose.yml    Coolify, Dokploy, Portainer, plain Docker (Traefik labels set)
nixpacks.toml         Nixpacks plan for Coolify / Dokploy / Railway autodetect
captain-definition    CapRover (schemaVersion 2 → ./Dockerfile)
Procfile              Dokku / Railway / Heroku process definition
app.json              Dokku / Heroku app metadata + /healthz health check
config/deploy.yml     Kamal 2 (fill in server IP, registry, domain)
netlify.toml          Netlify    — publish dir + headers + SPA fallback
wrangler.toml         Cloudflare Pages — build output dir
render.yaml           Render     — web service + health check
```

### Self-hosted PaaS competitors

Research notes on Coolify, Dokploy, Dokku, CapRover, Kamal, Kubero, ZaneOps and
Zeabur — star counts, licences, resource needs, and exactly which repo file each
one consumes — are in **[docs/DEPLOY-ALTERNATIVES.md](./docs/DEPLOY-ALTERNATIVES.md)**.

```bash
npm run docker:up      # build + run via docker-compose (Coolify/Dokploy compatible)
npm run deploy:caprover  # CapRover CLI (needs `caprover login` once)
npm run deploy:kamal     # Kamal (needs `gem install kamal` + config/deploy.yml filled in)
npm run deploy:dokku     # git push to your dokku remote
npm run start:serve      # Vercel's own `serve` static server, SPA fallback
npm run start:sirv       # lukeed/sirv, smallest static server
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

## 3. Downloading the single-file site

GitHub labels `.html` repo files as `text/plain`, so a raw link *displays* the
source instead of saving a file. Working options:

| Link | Behaviour |
| --- | --- |
| `<host>/download/sta1610-exam-prep.html` | Served by `sta1610/server.js` with `Content-Disposition: attachment` — saves as a real `.html` file in one click |
| `https://codeload.github.com/<owner>/<repo>/zip/refs/heads/<branch>` | GitHub sends `attachment` — downloads a zip of the repo, which contains the HTML |
| GitHub file page → **Download raw file** button | Saves the `.html` correctly |
| Raw URL + right-click → **Save link as…** | Saves the `.html` correctly |

The `/download/<file>` route is allow-listed to `sta1610-exam-prep.html`,
`sta1610-exam-prep.zip` and `index.html`; anything else returns 404.

## 4. Docker

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
