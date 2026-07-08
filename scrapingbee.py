#!/usr/bin/env python3
"""
ScrapingBee integration — для сайтов с тяжёлым антиботом (Avito, WB, Google).
1000 бесплатных кредитов. JS-рендеринг стоит 5 кредитов, без JS — 1 кредит.

Usage:
    from scrapingbee import ScrapingBee
    sb = ScrapingBee()
    html = sb.get("https://avito.ru/moskva/kvartiry", render_js=True, country="ru")
    data = sb.google("купить iPhone Москва")
    credits = sb.credits()
"""

import requests
import urllib.parse
import json

import os
API_KEY = os.getenv("SCRAPINGBEE_API_KEY", "")
BASE_URL = "https://app.scrapingbee.com/api/v1/"


class ScrapingBee:
    def __init__(self, api_key=None):
        self.api_key = api_key or API_KEY

    def credits(self):
        """Check remaining credits."""
        r = requests.get(f"{BASE_URL}usage", params={"api_key": self.api_key}, timeout=10)
        data = r.json()
        return {
            "total": data.get("max_api_credit", 0),
            "used": data.get("used_api_credit", 0),
            "remaining": data.get("max_api_credit", 0) - data.get("used_api_credit", 0),
        }

    def get(self, url, render_js=False, country=None, premium=False, wait=None,
            css_selector=None, headers=None, cookies=None):
        """
        Scrape URL through ScrapingBee.

        Args:
            url: Target URL
            render_js: Render JavaScript (5 credits instead of 1)
            country: Country code (us, gb, de, ru, etc.)
            premium: Use premium proxies (10-75 credits)
            wait: Wait for selector before returning
            css_selector: Extract only this CSS selector
            headers: Custom headers dict
            cookies: Custom cookies string
        """
        params = {
            "api_key": self.api_key,
            "url": url,
        }
        if render_js:
            params["render_js"] = "true"
        if country:
            params["country_code"] = country
        if premium:
            params["premium_proxy"] = "true"
        if wait:
            params["wait_for"] = wait
        if css_selector:
            params["extract_rules"] = json.dumps({"content": {"selector": css_selector, "type": "list"}})
        if headers:
            for k, v in headers.items():
                params[f"forward_headers_pure"] = "true"
        if cookies:
            params["cookies"] = cookies

        r = requests.get(BASE_URL, params=params, timeout=30)
        r.raise_for_status()
        return r.text

    def get_json(self, url, **kwargs):
        """Get and parse JSON."""
        text = self.get(url, **kwargs)
        return json.loads(text)

    def google(self, query, country="us", num=10):
        """
        Scrape Google search results.
        Uses ScrapingBee's Google search API (1 credit per search).
        """
        params = {
            "api_key": self.api_key,
            "search": "google",
            "search_query": query,
            "country_code": country,
            "nb_results": num,
        }
        r = requests.get(BASE_URL, params=params, timeout=15)
        r.raise_for_status()
        return r.text

    def avito(self, url):
        """Scrape Avito with JS rendering and RU proxy."""
        return self.get(url, render_js=True, country="ru")

    def wildberries(self, url):
        """Scrape Wildberries with JS rendering."""
        return self.get(url, render_js=True, country="ru")

    def screenshot(self, url, output_path="/tmp/sb_screenshot.png"):
        """Take screenshot of a page."""
        params = {
            "api_key": self.api_key,
            "url": url,
            "render_js": "true",
            "screenshot": "true",
            "screenshot_full_page": "true",
        }
        r = requests.get(BASE_URL, params=params, timeout=30)
        with open(output_path, "wb") as f:
            f.write(r.content)
        return output_path


if __name__ == "__main__":
    import sys
    sb = ScrapingBee()

    if len(sys.argv) < 2:
        credits = sb.credits()
        print(f"ScrapingBee credits: {credits['remaining']}/{credits['total']} remaining")
        print(f"\nUsage: scrapingbee.py <url> [--js] [--country ru] [--google 'query']")
        sys.exit(0)

    if sys.argv[1] == "--google":
        query = sys.argv[2]
        country = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == "--country" else "us"
        print(sb.google(query, country=country))
    elif sys.argv[1] == "--credits":
        print(json.dumps(sb.credits(), indent=2))
    else:
        url = sys.argv[1]
        render_js = "--js" in sys.argv
        country = None
        if "--country" in sys.argv:
            idx = sys.argv.index("--country")
            country = sys.argv[idx + 1]
        print(sb.get(url, render_js=render_js, country=country)[:5000])
