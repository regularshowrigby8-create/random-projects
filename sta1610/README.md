# STA1610 Exam Prep

A single-file revision workspace for **STA1610 — Introduction to Statistics**:
23 topic guides, past-paper question maps with independently worked solutions,
interactive calculators and a complete formula sheet.

The whole site lives in [`index.html`](./index.html) — no build step, no
dependencies to install, no framework. Open the file directly or serve the
folder.

## What is in here

| Section | Contents |
| --- | --- |
| Exam Prep | 2019–2025 source audit, 23 past-paper question write-ups with step-by-step solutions, revision tracking and a 2-hour practice timer |
| Topics 01–23 | Full theory notes, worked examples, formula boxes, exam traps |
| Calculators | Z-score, sample mean/sd, binomial, Poisson, confidence interval, z-test |
| Formula Sheet | Every formula used in the module, click any formula to copy it |

Progress, revision ticks and your theme choice are stored locally in the
browser (`localStorage`) — nothing leaves the device.

## Interface

* **Three-column workspace** — grouped topic sidebar, reading column, and an
  "on this page" rail on wide screens.
* **Top bar** with breadcrumb, reading-progress bar, visited-topics ring,
  search and theme switch.
* **Quick find** (`/` or `Ctrl/⌘ K`) searches every topic, heading and formula
  across all 23 pages.
* **Keyboard**: `[` / `]` previous/next topic, `T` light/dark, `?` shortcut
  sheet, `Esc` to close.
* **Motion** — staged page entrances, scroll reveals, pointer spotlight on
  cards, animated counters and a live progress ring, all disabled
  automatically under `prefers-reduced-motion`.
* Light and dark themes, responsive down to small phones, and a print
  stylesheet that prints the full notes.

## Run locally

```bash
npm start                       # from the repository root
# or without Node:
python3 -m http.server 8080 --directory sta1610
```

## Deploy

The folder is the publish directory. The repo ships its own static host
([`server.js`](./server.js)) with gzip, ETag caching and a `/healthz` endpoint,
plus configs for Netlify, Cloudflare Pages, Render, Docker/Fly and Surge.
Full instructions: [../DEPLOY.md](../DEPLOY.md).
