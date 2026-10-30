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
npm run urls      # print free zero-signup public URLs for the current commit
npm run build:pdf # rebuild sta1610-exam-prep.pdf from the HTML
```

## Downloads

| File | What it is |
| --- | --- |
| `sta1610-exam-prep.pdf` | 116-page A4 revision guide — cover, clickable contents, 155 bookmarks, every solution expanded |
| `sta1610-exam-prep.html` | the interactive single-file site |
| `sta1610-exam-prep-pdf.zip` | PDF + HTML + README bundle |
