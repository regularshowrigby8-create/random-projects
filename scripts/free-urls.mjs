#!/usr/bin/env node
/* Print zero-signup public URLs for this repository at the current commit.
 *
 *   npm run urls            # current HEAD
 *   npm run urls -- <sha>   # a specific commit / tag
 *
 * Every URL below is derived from the public GitHub repository and the
 * committed file, so nothing needs an account, a token or a build step.
 */
import { execSync } from 'node:child_process';

const REMOTE = process.env.GH_REPO || 'regularshowrigby8-create/random-projects';
const FILE = process.env.SITE_FILE || 'sta1610/index.html';

function git(cmd, fallback = '') {
  try {
    return execSync(cmd, { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim();
  } catch {
    return fallback;
  }
}

const arg = process.argv[2];
const sha = arg || git('git rev-parse HEAD') || 'main';
const shortSha = sha.slice(0, 7);
const blobUrl = `https://github.com/${REMOTE}/blob/${sha}/${FILE}`;

const rows = [
  {
    name: 'htmlpreview.github.io',
    url: `https://htmlpreview.github.io/?${blobUrl}`,
    status: 'verified — renders the full site, no account, no interstitial'
  },
  {
    name: 'raw.githack.com',
    url: `https://raw.githack.com/${REMOTE}/${sha}/${FILE}`,
    status: 'verified — correct content-type; visitors click once through an "External Content Notice"'
  },
  {
    name: 'rawcdn.githack.com',
    url: `https://rawcdn.githack.com/${REMOTE}/${sha}/${FILE}`,
    status: 'verified — same as raw.githack, CDN edge'
  },
  {
    name: 'cdn.statically.io',
    url: `https://cdn.statically.io/gh/${REMOTE}/${sha}/${FILE}`,
    status: 'unverified — the service did not respond when tested'
  },
  {
    name: 'cdn.jsdelivr.net (source only)',
    url: `https://cdn.jsdelivr.net/gh/${REMOTE}@${sha}/${FILE}`,
    status: 'serves text/plain by design — useful for diffing, not for visiting'
  },
  {
    name: 'raw.githubusercontent.com (source only)',
    url: `https://raw.githubusercontent.com/${REMOTE}/${sha}/${FILE}`,
    status: 'serves text/plain — shows the source, not the site'
  }
];

console.log(`\nFree, zero-signup URLs for ${REMOTE}`);
console.log(`commit ${shortSha} · file ${FILE}\n`);
for (const row of rows) {
  console.log(`  ${row.name}`);
  console.log(`    ${row.url}`);
  console.log(`    ${row.status}\n`);
}
console.log('Regenerate after a new commit with:  npm run urls\n');
