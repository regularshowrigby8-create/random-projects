# random-projects

a building station for websites and applications

## Projects

| Project | What it is | Deploy |
| --- | --- | --- |
| [`sta1610/`](./sta1610) | STA1610 statistics exam-prep workspace — 23 topic guides, past-paper solutions, calculators, formula sheet | `npm start` (built-in host) |

## Run / deploy

```bash
npm start        # serves sta1610/ on http://localhost:8080
```

The repo carries its own deploy layer: a dependency-free Node static host
(`sta1610/server.js`) plus ready configs for Coolify, Dokploy, Dokku, CapRover,
Kamal, Docker, Netlify, Cloudflare Pages, Render and Surge.

* [DEPLOY.md](./DEPLOY.md) — how to deploy, option by option
* [docs/DEPLOY-ALTERNATIVES.md](./docs/DEPLOY-ALTERNATIVES.md) — research on the
  GitHub projects that compete with Vercel, with stars, licences and what each
  one needs from a repository
* [docs/FREE-HOSTING.md](./docs/FREE-HOSTING.md) — niche free, zero-account
  hosts that read a public repo, with what was actually verified

```bash
npm run urls     # print free zero-signup public URLs for the current commit
```
