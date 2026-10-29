# Vercel alternatives on GitHub — research & what is wired into this repo

You were right: plenty of them exist, they are serious projects, and several are
designed to be driven entirely from a repository. This document records what was
found, what was verified **in this environment**, and what each option still
needs before it can hand out a public domain.

Star counts, languages, licences and last-push dates were read from the GitHub
API on **2026-10-30**.

## 1. The self-hosted PaaS tier (the real Vercel/Netlify competitors)

| Project | Stars | Language | Licence | What it is | Repo file it wants |
| --- | --- | --- | --- | --- | --- |
| [coollabsio/coolify](https://github.com/coollabsio/coolify) | 65.3k | PHP | Apache-2.0 | Self-hostable PaaS, closest functional match to "Vercel + Heroku" on your own box | `docker-compose.yml`, `Dockerfile`, or `nixpacks.toml` |
| [Dokploy/dokploy](https://github.com/Dokploy/dokploy) | 38.1k | TypeScript | Apache-2.0 core (paid features source-available) | Modern dashboard, Docker Compose + Traefik, fast-moving | `docker-compose.yml` / `Dockerfile` |
| [dokku/dokku](https://github.com/dokku/dokku) | 32.2k | Go | MIT | Smallest-surface, CLI-first `git push` PaaS; the most Unix-shaped option | `Procfile`, `app.json`, `Dockerfile` |
| [caprover/caprover](https://github.com/caprover/caprover) | 15.2k | TypeScript | Apache-2.0 + appendix | Docker + nginx + ACME with a UI and 350+ one-click apps | `captain-definition` (required) |
| [basecamp/kamal](https://github.com/basecamp/kamal) | 14.7k | Ruby | MIT | Deployment tool rather than a dashboard; Docker over SSH | `config/deploy.yml` |
| [kubero-dev/kubero](https://github.com/kubero-dev/kubero) | 4.5k | TypeScript | GPL-3.0 | PaaS on Kubernetes for people who want k8s underneath | Helm/buildpacks |
| [zane-ops/zane-ops](https://github.com/zane-ops/zane-ops) | 1.4k | Python | custom | Younger Coolify-style PaaS, nice UI | Docker Compose |
| [zeabur-oss/zeabur](https://github.com/zeabur-oss/zeabur) | 0.5k | Rust | Apache-2.0 | Self-hosted PaaS on your own Kubernetes | `zbpack.json` |

Both Coolify and Dokploy describe themselves explicitly as open-source Vercel
alternatives, and comparative reviews rank Coolify/Dokploy/Dokku/CapRover as the
four practical self-hosted choices, with Kamal as the "no dashboard, SSH +
Docker" option ([Stormkit, 2026](https://www.stormkit.io/blog/best-self-hosted-vercel-alternatives),
[pethost, 2026](https://pethost.dev/blog/coolify-vs-dokploy-vs-caprover-vs-dokku/),
[Cloudzy, 2026](https://cloudzy.com/blog/self-hosted-paas-alternatives/)).

**What all of them need:** a VPS (or a machine) running Docker, root/SSH access,
and — for a public domain — either the server's IP plus a DNS record, or a
domain you point at it. They are not "paste a URL, get a domain" services; the
platform is the repo, the domain still comes from your DNS.

Resource floors reported in the comparisons above: Dokku ~1 GB RAM, CapRover
~1 GB, Coolify 2 vCPU / 2 GB / 10 GB disk, Dokploy ~2 GB.

## 2. The lightweight static-server tier (no PaaS, no dashboard)

| Project | Stars | Language | Licence | Why it matters here |
| --- | --- | --- | --- | --- |
| [caddyserver/caddy](https://github.com/caddyserver/caddy) | 78.5k | Go | Apache-2.0 | Reverse proxy with automatic HTTPS in front of any static host |
| [vercel/serve](https://github.com/vercel/serve) | 9.9k | TypeScript | MIT | Vercel's own static file server; `--single` gives SPA fallback |
| [static-web-server/static-web-server](https://github.com/static-web-server/static-web-server) | 2.4k | Rust | Apache-2.0 | Single high-performance binary, tiny memory footprint |
| [lukeed/sirv](https://github.com/lukeed/sirv) | 1.2k | JavaScript | MIT | Smallest possible static server/CLI |

## 3. What was actually verified in this environment

The sandbox reaches GitHub and the npm/PyPI registries only — `api.netlify.com`,
`api.cloudflare.com`, `surge.sh`, `api.render.com`, `api.fly.io` and
`api.vercel.com` all fail DNS/connection, and there is **no Docker daemon**. So:

| Option | Can it run here? | Evidence |
| --- | --- | --- |
| In-repo host (`sta1610/server.js`) | **Yes — running now** | `/` 200 (387,601 B → 93,864 B gzip), `304` on ETag, `/healthz` healthy |
| `vercel/serve` (`--single`) | **Yes** | `/` 200, deep path `/topic/poisson` 200, bound to `0.0.0.0`, reachable on the non-loopback IP |
| `lukeed/sirv` (`--single --host 0.0.0.0`) | **Yes** | `/` 200 and deep path 200 on the non-loopback IP |
| Coolify / Dokploy / CapRover / Dokku / Kamal | **No** — needs a Docker daemon + VPS | configs prepared and syntax-validated only |
| Netlify / Cloudflare / Render / Fly / Surge | **No** — APIs unreachable, no credentials | configs prepared only |

## 4. Files now committed for each platform

| Platform | File in repo | What it does |
| --- | --- | --- |
| Coolify / Dokploy / plain Docker | `docker-compose.yml`, `Dockerfile`, `.dockerignore` | Builds the image, exposes 8080, health-checks `/healthz`, Traefik labels pre-set |
| Coolify / Dokploy / Railway autodetect | `nixpacks.toml` | Node 20 plan with `node sta1610/server.js` as the start command |
| CapRover | `captain-definition` | `schemaVersion 2` → `./Dockerfile` (the required file; malformed/missing ones are the top cause of CapRover restart loops) |
| Dokku | `Procfile`, `app.json` | `web: node sta1610/server.js` + health check on `/healthz`, formation and metadata |
| Kamal | `config/deploy.yml` | Service, registry, proxy host, `app_port: 8080`, automatic HTTPS — four `TODO` values to fill in |
| Render | `render.yaml` | Web service + `healthCheckPath: /healthz` |
| Netlify / Cloudflare Pages / Surge | `netlify.toml`, `wrangler.toml`, npm scripts | Publish dir `sta1610`, SPA fallback, cache headers |

## 5. Recommendation, in order of effort

1. **Nothing to sign up for (done)** — `npm start` runs the in-repo host; this is
   what the current live preview serves.
2. **Cheapest route to a real domain** — rent any small VPS (€4–5/month class),
   install Coolify (`curl -fsSL https://coolify.io/install.sh | bash`) or
   Dokploy, add this repository as a resource, set the domain in the UI →
   automatic Let's Encrypt HTTPS. ~15 minutes, and every file it needs is
   already committed.
3. **Simplest single app** — Dokku: `dokku apps:create sta1610-exam-prep`,
   add the git remote, `git push dokku main`, `dokku letsencrypt:enable`.
   MIT licensed, ~1 GB RAM, no dashboard to secure.
4. **If you would rather not run a server at all** — Netlify/Cloudflare/Surge
   via the npm scripts in `package.json`; identical files, but those APIs must be
   called from your machine or CI, not from this sandbox.

None of these can be *fully* installed inside this repository: a PaaS owns
Docker, ports 80/443, certificates and DNS, and it must sit on a host you
control. What a repository can do — and now does — is carry a correct build and
deploy contract for every one of them, so any of them will deploy this site with
no further configuration.
