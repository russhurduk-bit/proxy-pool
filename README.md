# Proxy Pool

A universal proxy-rotation manager with a single JSON config, a free-proxy harvester, a rotating scraper, a ScrapingBee wrapper for hard anti-bot targets, and a multi-country SEO position checker.

## Features

- **Unified proxy manager** (`proxy_pool.py`) — one config for the whole server. Select proxies by `tag` (e.g. `youtube`, `scraping`, `osint`, `telegram`, `reliable`) and/or `country`. Emits ready-to-use formats: `requests` dict, plain URL, `http://`, `socks5h://`, plus helpers for yt-dlp and n8n.
- **Free-proxy harvester** (`harvest_free.py`) — pulls candidates from several public proxy lists, validates them live in parallel, additionally probes which ones pass Instagram's auth wall, and writes the working set into `config.json` under `free_proxies` (Instagram-capable first).
- **Rotating scraper** (`scraper.py`) — `requests`-based `Scraper` with proxy rotation, retries, and randomized user-agents (`get` / `get_json` / `post`), a `check_geo()` exit-IP inspector, plus a Playwright-based `BrowserScraper` for JS-heavy anti-bot sites.
- **ScrapingBee wrapper** (`scrapingbee.py`) — thin client for the ScrapingBee API: JS rendering, country targeting, premium proxies, CSS extract rules, Google SERP scraping, screenshots, and a credits check. Convenience methods for Avito and Wildberries.
- **SEO position checker** (`seo_checker.py`) — checks a domain's Google ranking from multiple countries by routing each request through a country-matched proxy and the corresponding Google TLD.

## Tech stack

- Python 3
- `requests` for HTTP and proxy transport
- `concurrent.futures` for parallel proxy validation
- Playwright (Node) for the browser scraper (`testpad_solver.js` is a companion Node script)
- ScrapingBee API for anti-bot fallback

## Setup

```bash
# 1. Install dependencies
pip install requests
# (optional) for BrowserScraper:  npm i playwright  &&  npx playwright install chromium

# 2. Configure environment
cp .env.example .env
# then edit .env and add your ScrapingBee key

# 3. Configure proxies — edit config.json (see format below)
```

### config.json format

`config.json` in the project root defines all proxies. Replace the placeholders (`<...>` and `0.0.0.0`) with real values:

```json
{
  "webshare": {
    "api_key": "<WEBSHARE_API_KEY>",
    "username": "<USERNAME>",
    "password": "<PASSWORD>"
  },
  "swiss": {
    "host": "0.0.0.0",
    "port": 8000,
    "username": "<USERNAME>",
    "password": "<PASSWORD>",
    "protocol": "socks5h",
    "country": "CH",
    "tags": ["youtube", "scraping", "reliable"]
  },
  "proxies": [
    {
      "host": "0.0.0.0",
      "port": 6754,
      "username": "<USERNAME>",
      "password": "<PASSWORD>",
      "country": "GB",
      "tags": ["youtube", "scraping", "osint", "telegram"]
    }
  ]
}
```

- `webshare` — account-level credentials used as the default auth for any entry in `proxies` that omits its own `username`/`password`.
- `swiss` — a single premium/self-hosted proxy (arbitrary name); note `protocol` can be `http` or `socks5h`.
- `proxies` — your primary rotating proxies; each may override `username`, `password`, `protocol` (default `http`), and `country` (default `??`), and carries a list of `tags`.
- `free_proxies` — auto-managed by `harvest_free.py`; you do not need to write this by hand.

## Usage

Proxy pool CLI:

```bash
python proxy_pool.py list [tag]     # list matching proxies
python proxy_pool.py get [tag]      # print one random matching proxy URL
python proxy_pool.py youtube        # best proxy URL for yt-dlp
python proxy_pool.py n8n            # proxy config JSON for n8n HTTP Request node
python proxy_pool.py test [tag]     # live-test proxies against httpbin.org/ip
```

Harvest free proxies into `config.json`:

```bash
python harvest_free.py --target 50 --validate-url https://api.ipify.org --workers 200
```

Scrape through the pool:

```bash
python scraper.py "https://example.com" --tag scraping --country GB [--json]
```

ScrapingBee:

```bash
python scrapingbee.py                       # show remaining credits
python scrapingbee.py "https://site" --js --country ru
python scrapingbee.py --google "buy iphone" --country us
```

SEO position check:

```bash
python seo_checker.py "keyword" yourdomain.com --countries GB,US,JP
```

Library usage:

```python
from proxy_pool import ProxyPool
pool = ProxyPool()
proxy = pool.get(tag="youtube")            # a Proxy object
proxies = pool.get_requests_format(tag="scraping")   # dict for requests
```

## Notes

- **ScrapingBee** requires `SCRAPINGBEE_API_KEY` (see `.env.example`). JS rendering costs ~5 credits per call, plain fetch ~1, premium proxies 10–75.
- **BrowserScraper** shells out to Node/Playwright and expects a working Node environment (the source references a `/root/browser-pilot` working directory for the inline script).
- `harvest_free.py` overwrites the `free_proxies` key in `config.json` on success and leaves the file untouched if no working proxies are found.
- Country codes in `seo_checker.py` map to localized Google domains (GB→co.uk, JP→co.jp, etc.); it deliberately sleeps between requests to avoid hammering Google.
