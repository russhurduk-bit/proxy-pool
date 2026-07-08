#!/usr/bin/env python3
"""
SEO Position Checker — проверка позиций сайта в Google из разных стран.

Usage:
    python3 seo_checker.py "ключевое слово" "yourdomain.com" [--countries GB,US,JP]
"""

import sys
import re
import time
import random
import requests
from proxy_pool import ProxyPool

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]


def check_google_position(query, domain, proxy, num_results=30):
    """Check domain position in Google for a query via proxy."""
    url = "https://www.google.com/search"
    params = {
        "q": query,
        "num": num_results,
        "hl": "en",
    }

    # Set Google domain based on proxy country
    country_domains = {
        "GB": "https://www.google.co.uk/search",
        "US": "https://www.google.com/search",
        "JP": "https://www.google.co.jp/search",
        "ES": "https://www.google.es/search",
        "CH": "https://www.google.ch/search",
        "DE": "https://www.google.de/search",
        "RU": "https://www.google.ru/search",
    }
    search_url = country_domains.get(proxy.country, url)

    try:
        resp = requests.get(
            search_url, params=params,
            proxies=proxy.requests_format,
            headers={"User-Agent": random.choice(USER_AGENTS)},
            timeout=15
        )
        html = resp.text

        # Extract search result URLs
        links = re.findall(r'<a href="/url\?q=(https?://[^&"]+)', html)
        if not links:
            links = re.findall(r'href="(https?://[^"]+)"', html)

        position = 0
        for i, link in enumerate(links, 1):
            if domain.lower() in link.lower():
                position = i
                break

        return {
            "country": proxy.country,
            "proxy": f"{proxy.host}:{proxy.port}",
            "position": position if position > 0 else "not found",
            "total_results_checked": len(links),
        }
    except Exception as e:
        return {
            "country": proxy.country,
            "proxy": f"{proxy.host}:{proxy.port}",
            "error": str(e),
        }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: seo_checker.py <query> <domain> [--countries GB,US,JP]")
        sys.exit(1)

    query = sys.argv[1]
    domain = sys.argv[2]
    countries = None
    if "--countries" in sys.argv:
        idx = sys.argv.index("--countries")
        countries = sys.argv[idx + 1].split(",")

    pool = ProxyPool()

    # Get unique country proxies
    seen_countries = set()
    proxies_to_check = []
    for p in pool.get_all(tag="osint"):
        if countries and p.country not in countries:
            continue
        if p.country not in seen_countries:
            seen_countries.add(p.country)
            proxies_to_check.append(p)

    print(f"Checking '{query}' for {domain} in {len(proxies_to_check)} countries...\n")

    for proxy in proxies_to_check:
        result = check_google_position(query, domain, proxy)
        pos = result.get("position", "error")
        country = result.get("country", "?")
        print(f"  {country}: position {pos}")
        time.sleep(2)  # Don't hammer Google
