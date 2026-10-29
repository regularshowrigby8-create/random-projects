# Niche, free hosting for a repo — research & verified results

Round two of the hosting research: not the big PaaS platforms, but small,
**free, zero-account** options that turn a public repository into a live URL.
Star counts, licences and last-push dates were read from the GitHub API on
**2026-10-30**; behaviour was tested by actually requesting the site through each
service.

Run `npm run urls` at any commit to print the current links.

## 1. The winner: HTML proxies that read your repo (no account at all)

| Service | Repo | Stars | Licence | How it works | Tested result |
| --- | --- | --- | --- | --- | --- |
| **htmlpreview.github.io** | [htmlpreview/htmlpreview.github.com](https://github.com/htmlpreview/htmlpreview.github.com) | 1.8k | none declared | `https://htmlpreview.github.io/?<github blob URL>` fetches the raw file and writes it into a document so the browser renders it | ✅ **Renders the whole site** — headings, sidebar, tables, exam cards all parsed; no interstitial |
| **raw.githack.com** | [neoascetic/rawgithack](https://github.com/neoascetic/rawgithack) | 683 | MIT | Reverse-proxies raw files with the correct `Content-Type` | ⚠️ Works, but visitors hit an *"External Content Notice — one more step"* page and must click through |
| **rawcdn.githack.com** | same | 683 | MIT | CDN variant of the above | ⚠️ Same interstitial |
| **cdn.statically.io** | [staticallyio/statically](https://github.com/staticallyio/statically) | 609 | none declared | Free CDN for GitHub/GitLab/Bitbucket/npm | ❌ Did not respond on 2026-10-30 (may be down) |
| **gitloaf.com** | [albibos/gitloaf](https://github.com/albibos/gitloaf) | 12 | MIT | Same idea as githack, Node/Express | ⚠️ Self-declared *"no longer actively maintained"*; self-host only |
| **gitcdn.link** | — | — | — | Formerly the popular alternative | ❌ Effectively dead; last public activity 2023 |

**Do not be fooled by the CDNs:** `cdn.jsdelivr.net/gh/...` ([jsdelivr/jsdelivr](https://github.com/jsdelivr/jsdelivr),
6.4k ★) and `raw.githubusercontent.com` both serve `text/plain` for `.html`
files, so a visitor sees the source code, not the site. Verified directly.

### Caveats for the proxy route (applies to htmlpreview / githack)

* The URL is long and not memorable, and cannot be given a custom domain.
* The repository must be **public** — ours is.
* These are best-effort community services: no SLA, rate limits, and they can
  disappear (gitcdn.link did).
* Pages render inside an iframe on a foreign origin, where browsers may block
  `localStorage`. **This site was hardened for that** (see §4).
* Branch names containing `/` break these URLs — use the **commit SHA**; the URL
  is then pinned to an immutable tree, which is also a feature.

## 2. Free tiers that need a free account (no payment, no card)

| Service | Repo / CLI | Stars | Free URL | What it needs |
| --- | --- | --- | --- | --- |
| **Surge** | npm `surge` | — | `*.surge.sh` (custom domains allowed) | Email + password on first deploy; interactive, so run it from your machine |
| **Netlify** | [netlify/cli](https://github.com/netlify/cli) 1.9k ★ | `*.netlify.app` | Account + `npx netlify-cli login`; config already in `netlify.toml` |
| **Cloudflare Pages** | [cloudflare/workers-sdk](https://github.com/cloudflare/workers-sdk) 4.7k ★ | `*.pages.dev` | Account + `npx wrangler login`; config already in `wrangler.toml` |
| **Deno Deploy** | [denoland/deployctl](https://github.com/denoland/deployctl) 367 ★ | `*.deno.dev` | Free token, `deployctl deploy` |
| **Hugging Face Spaces** | [huggingface/huggingface_hub](https://github.com/huggingface/huggingface_hub) 4.0k ★ | `*.hf.space` | Free account + write token — genuinely generous for static sites |
| **Codeberg Pages** | — | — | `*.codeberg.page` | Free non-profit account (not GitHub), git push |
| **GitLab Pages** | — | — | `*.gitlab.io` | Free account, repo mirror + CI job |
| **IPFS** | [ipfs-shipyard/ipfs-deploy](https://github.com/ipfs-shipyard/ipfs-deploy) 1.2k ★ | `gateway/ipfs/<CID>` | Pinning service credential; the tool itself is an abandoned 2022 proof of concept |

## 3. Zero-account static servers (run from the repo, any host)

| Tool | Stars | Licence | Command |
| --- | --- | --- | --- |
| [vercel/serve](https://github.com/vercel/serve) | 9.9k | MIT | `npm run start:serve` (uses `--single` SPA fallback) |
| [lukeed/sirv](https://github.com/lukeed/sirv) | 1.2k | MIT | `npm run start:sirv` |
| [static-web-server/static-web-server](https://github.com/static-web-server/static-web-server) | 2.4k | Apache-2.0 | single binary, ~few MB RAM |
| `sta1610/server.js` (this repo) | — | — | `npm start` — gzip, ETag, `/healthz` |

Both npm servers were installed and run here: `/` **and** deep paths returned
`200`, bound to `0.0.0.0`, reachable on the non-loopback interface.

## 4. What changed in the site because of this research

* **`localStorage` fallback** — a tiny in-memory shim runs before anything else
  if the browser blocks storage (sandboxed/proxied iframes, strict privacy
  modes). Without it, the original `updateProgress()` would throw on navigation.
* **Factual counters are no longer animated** — the hero numbers (*48 entries,
  23 guides, 3 gap fillers*) are claims, not decoration. A counting animation
  meant a snapshot taken mid-animation (crawler, print view, proxy harvest) read
  "0". They now always render their committed value. Verified through
  htmlpreview: 48 / 23 / 3 render correctly with no JavaScript animation.
* Verified in a simulated blocked-storage browser: navigation, theme toggle,
  quick find, calculators and revision ticks all still work, **0 console errors**.

## 5. Verdict

* Want a link you can paste in a WhatsApp group **right now, with no signup**:
  the `htmlpreview.github.io` URL from `npm run urls` (verified rendering).
* Want a short, permanent, brandable address: still needs one of the account
  tiers in §2 — all of which already have their config committed.
