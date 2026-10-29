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
(`sta1610/server.js`) plus ready configs for Netlify, Cloudflare Pages, Render,
Fly/Docker and Surge. See [DEPLOY.md](./DEPLOY.md).
