# 鱼了圈海选赛 · 角色人气榜

Mobile-friendly static ranking board for the one-week fan activity. It contains the 24 products supplied in `Links and Characters.txt`.

## Data-source status

The Weidian Open Platform exists and uses registered applications, but the publicly accessible materials reviewed for this project did not establish an endpoint, permission scope, response field, or rate limit for reading sales counts of these arbitrary product links. The provided `<em class="sale-count">销量 0</em>` observation is not enough to establish that the page's rendered markup is stable or authoritative. The project therefore does **not** scrape Weidian or claim the displayed zeroes are verified sales. Every initial `sales: 0` is explicitly marked `salesVerified: false`.

The collector is a provider adapter. Configure `SALES_PROVIDER_URL` as a GitHub Actions repository secret only after obtaining an authorized endpoint/feed and confirming its schema and terms. The endpoint must be HTTPS and return JSON in this shape:

```json
{"sales":{"weizhi":12,"yueqi":8}}
```

Keys are character IDs from `data.json`; values must be non-negative integers. Missing or invalid entries retain their previous values. If no valid sales values arrive, the script exits without modifying the data. No API key is embedded in the browser or repository. If the official Weidian API becomes available to this shop, implement its documented authentication and response mapping inside `fetch_provider`; do not infer undocumented API details.

## Files

- `index.html`: semantic page structure and dashboard labels.
- `_headers`: tells Cloudflare Pages not to cache the live ranking JSON, so the browser's 30-second check can see new deployments promptly.
- `style.css`: responsive light dashboard styling.
- `app.js`: safely renders product records, sorts sales descending with configured order as tie-breaker, searches names, and refreshes JSON every 30 seconds.
- `data.json`: event metadata and all 24 products. Edit this file to add or remove products; no frontend changes are needed. Give each new product a unique lowercase `id`, sequential `order`, a valid HTTPS Weidian URL, and initial `sales: 0`, `salesVerified: false`.
- `update_sales.py`: standard-library Python collector. Reads the authorized feed, validates records, preserves last good values, writes atomically, and logs failures without exposing URL credentials.
- `.github/workflows/update.yml`: GitHub Actions scheduled/manual run and data commit.
- `.gitignore`: ignores local Python files and temporary writes.

## Deployment tutorial

### 1. Create and upload the GitHub repository

1. Sign in to GitHub and create a repository named `yulequan-ranking`. Public is convenient for a short fan event and makes standard GitHub-hosted Actions runner usage free; private repositories may be subject to account plan included minutes/storage and overage rules.
2. Upload these project files, preserving `.github/workflows/update.yml`.
3. Open **Settings → Actions → General** and allow actions. The workflow uses the repository-provided `GITHUB_TOKEN` with `contents: write` to commit only changes to `data.json`.

### 2. Connect Cloudflare Pages

1. In Cloudflare, open **Workers & Pages → Create application → Pages → Connect to Git** and choose the repository.
2. Choose **None** as the framework preset. Set build command to `exit 0` and build output directory to `.` (repository root). This is a plain static site; Python does not run on Pages.
3. Deploy. Cloudflare provides a `*.pages.dev` URL. HTTPS is enabled for the Pages URL.

### 3. Configure the authorized data provider

1. Ask the shop owner/provider for written permission and documented access. Verify which sales measure is returned, update cadence, authentication, and rate limits. The Weidian developer portal may require application registration/approval; public product visibility alone does not establish permission for automated collection.
2. Configure that service to return the JSON format documented above. If it needs a bearer/API credential, configure it at the provider and adapt `fetch_provider` to send a GitHub secret in an authorization header. Never put credentials in `data.json`, source code, or browser JavaScript.
3. In GitHub, open **Settings → Secrets and variables → Actions → New repository secret**; name it `SALES_PROVIDER_URL` and enter the private HTTPS feed URL. If no authorized feed is available, leave this unset: the job safely makes no changes and the board remains an initial placeholder.
4. To test, go to **Actions → Update sales data → Run workflow**. Read the step log. A successful run with changed data commits it to the repository; Pages then deploys the updated static JSON. A failure retains existing counts. Scheduled jobs are best-effort and may be delayed; they do not promise exact-minute execution.

### 4. Verify, share, and retire

1. Check the workflow run and its commit timestamp. Open `https://YOUR-PROJECT.pages.dev/data.json` and verify only provider-confirmed values are marked `salesVerified: true`.
2. Open the Pages URL in a phone browser and test search, card links, and refresh. Ask users in Mainland China to try the URL on their own networks and mobile browsers before wide sharing. Cloudflare does not guarantee reliable reachability in Mainland China; consider a locally reachable host if access tests fail.
3. Share the public Pages URL on Weibo. The dashboard refreshes the static JSON every 30 seconds; backend collection is scheduled independently at minutes 17 and 47 each hour.
4. After the event, disable the workflow under **Actions → Update sales data → … → Disable workflow**. You may delete/archive the GitHub repository and Cloudflare Pages project from their dashboards.

## Cost and limits (checked 20 Oct 2026)

- Cloudflare Pages Free currently documents up to 500 builds/month, one concurrent build, 20,000 files/site, and 25 MiB per file. Static asset requests are unlimited and free. This project is well below the file limits; each data commit triggers a Pages build, so monitor build use if the provider reports frequent changes.
- GitHub documents standard hosted runner use as free for public repositories. Private repository included minutes and storage depend on account plan; GitHub's limits and billing terms can change. Scheduled workflows may be delayed or dropped under GitHub scheduling behavior, so this is approximate polling, not a guaranteed clock.
- Cloudflare Workers Cron was considered but is not selected: it would require adding a separate Worker and storage/publishing bridge for a static Pages JSON file. Workers Free currently lists 100,000 requests/day and 10 ms CPU per invocation, and Cron is supported, but the GitHub workflow keeps this small project easier to inspect and maintain.
- Hosting is expected to fit free tiers for this one-week event. Third-party provider/API charges, private GitHub Actions overages, custom domains, and future plan changes are not included or guaranteed free.

## Official references

- [Cloudflare Pages limits](https://developers.cloudflare.com/pages/platform/limits/)
- [Cloudflare Pages Functions pricing and static asset requests](https://developers.cloudflare.com/pages/functions/pricing/)
- [Cloudflare Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/)
- [Cloudflare Workers limits](https://developers.cloudflare.com/workers/platform/limits/)
- [Cloudflare Cron Triggers](https://developers.cloudflare.com/workers/configuration/cron-triggers/)
- [GitHub Actions billing and usage](https://docs.github.com/en/actions/concepts/billing-and-usage)
- [GitHub Actions limits](https://docs.github.com/en/actions/reference/limits)
- [Weidian Open Platform](https://open.weidian.com/)

