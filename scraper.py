#!/usr/bin/env python3
"""
Universal Scraper — скрейпинг любого сайта через пул прокси с ротацией.

Usage:
    from scraper import Scraper
    s = Scraper()
    html = s.get("https://avito.ru/moskva/kvartiry")
    data = s.get_json("https://api.example.com/data")

CLI:
    python3 scraper.py "https://avito.ru/moskva/kvartiry" [--tag scraping] [--country GB]
"""

import sys
import time
import random
import requests
from proxy_pool import ProxyPool

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
]


class Scraper:
    def __init__(self, tag="scraping", country=None, retries=3, timeout=15):
        self.pool = ProxyPool()
        self.tag = tag
        self.country = country
        self.retries = retries
        self.timeout = timeout

    def _get_session(self):
        proxy = self.pool.get(tag=self.tag, country=self.country)
        session = requests.Session()
        session.proxies = proxy.requests_format
        session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
        })
        return session, proxy

    def get(self, url, headers=None, **kwargs):
        """GET request with proxy rotation and retries."""
        last_error = None
        for attempt in range(self.retries):
            session, proxy = self._get_session()
            if headers:
                session.headers.update(headers)
            try:
                resp = session.get(url, timeout=self.timeout, **kwargs)
                resp.raise_for_status()
                return resp.text
            except Exception as e:
                last_error = e
                time.sleep(1)
        raise last_error

    def get_json(self, url, headers=None, **kwargs):
        """GET JSON with proxy rotation."""
        last_error = None
        for attempt in range(self.retries):
            session, proxy = self._get_session()
            if headers:
                session.headers.update(headers)
            try:
                resp = session.get(url, timeout=self.timeout, **kwargs)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                last_error = e
                time.sleep(1)
        raise last_error

    def post(self, url, data=None, json_data=None, headers=None, **kwargs):
        """POST request with proxy rotation."""
        last_error = None
        for attempt in range(self.retries):
            session, proxy = self._get_session()
            if headers:
                session.headers.update(headers)
            try:
                resp = session.post(url, data=data, json=json_data, timeout=self.timeout, **kwargs)
                resp.raise_for_status()
                return resp.text
            except Exception as e:
                last_error = e
                time.sleep(1)
        raise last_error

    def check_geo(self):
        """Check exit IP and geo for all proxies."""
        results = []
        for proxy in self.pool.get_all(tag=self.tag):
            try:
                r = requests.get("https://ipinfo.io/json",
                                 proxies=proxy.requests_format, timeout=10)
                info = r.json()
                results.append({
                    "proxy": f"{proxy.country} {proxy.host}",
                    "exit_ip": info.get("ip"),
                    "city": info.get("city"),
                    "country": info.get("country"),
                    "org": info.get("org"),
                })
            except Exception as e:
                results.append({"proxy": f"{proxy.country} {proxy.host}", "error": str(e)})
        return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scrape URL through proxy pool")
    parser.add_argument("url", help="URL to scrape")
    parser.add_argument("--tag", default="scraping", help="Proxy tag filter")
    parser.add_argument("--country", default=None, help="Country filter (GB, US, etc)")
    parser.add_argument("--json", action="store_true", help="Parse as JSON")
    args = parser.parse_args()

    s = Scraper(tag=args.tag, country=args.country)
    try:
        if args.json:
            import json
            print(json.dumps(s.get_json(args.url), indent=2, ensure_ascii=False))
        else:
            print(s.get(args.url)[:5000])
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


class BrowserScraper:
    """Scraper using Playwright for anti-bot sites (Avito, WB, etc)."""

    def __init__(self, tag="scraping", country=None):
        self.pool = ProxyPool()
        self.tag = tag
        self.country = country

    def get(self, url, wait_for=None, timeout=30000):
        """Scrape URL using headless browser through proxy."""
        import subprocess
        proxy = self.pool.get(tag=self.tag, country=self.country)

        script = f"""
const {{ chromium }} = require('playwright');
(async () => {{
  const browser = await chromium.launch({{
    headless: true,
    args: ['--no-sandbox'],
    proxy: {{ server: '{proxy.url_http}' }}
  }});
  const page = await browser.newPage();
  await page.goto('{url}', {{ waitUntil: 'domcontentloaded', timeout: {timeout} }});
  await page.waitForTimeout(3000);
  {'await page.waitForSelector("' + wait_for + '", {timeout: 10000});' if wait_for else ''}
  const html = await page.content();
  process.stdout.write(html);
  await browser.close();
}})();
"""
        result = subprocess.run(
            ["node", "-e", script],
            capture_output=True, text=True, timeout=timeout // 1000 + 15,
            cwd="/root/browser-pilot"
        )
        if result.returncode != 0:
            raise Exception(f"Browser error: {result.stderr[:200]}")
        return result.stdout
