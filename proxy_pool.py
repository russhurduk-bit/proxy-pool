#!/usr/bin/env python3
"""
Universal Proxy Pool — единый прокси-менеджер для всего сервера.
Используется для: скрейпинга, OSINT, YouTube, n8n, SEO-чекера.

Usage:
    from proxy_pool import ProxyPool
    pool = ProxyPool()
    proxy = pool.get(tag="youtube")          # получить прокси для YouTube
    proxy = pool.get(country="GB")           # получить GB прокси
    proxy = pool.get(tag="scraping")         # случайный для скрейпинга
    proxies = pool.get_all(tag="osint")      # все OSINT прокси
    proxy_dict = pool.get_requests_format()  # для requests library
    proxy_url = pool.get_url()               # socks5h://user:pass@host:port
"""

import json
import os
import random
from pathlib import Path
from typing import Optional

CONFIG_PATH = Path(__file__).parent / "config.json"


class Proxy:
    def __init__(self, host, port, username, password, protocol="http", country="??", tags=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.protocol = protocol
        self.country = country
        self.tags = tags or []

    @property
    def _auth(self):
        return f"{self.username}:{self.password}@" if self.username else ""

    @property
    def url(self):
        return f"{self.protocol}://{self._auth}{self.host}:{self.port}"

    @property
    def url_http(self):
        return f"http://{self._auth}{self.host}:{self.port}"

    @property
    def url_socks5(self):
        return f"socks5h://{self._auth}{self.host}:{self.port}"

    @property
    def requests_format(self):
        url = self.url
        return {"http": url, "https": url}

    @property
    def aiohttp_format(self):
        return self.url_socks5

    def __repr__(self):
        return f"Proxy({self.country} {self.host}:{self.port} [{','.join(self.tags)}])"


class ProxyPool:
    def __init__(self, config_path=None):
        path = config_path or CONFIG_PATH
        with open(path) as f:
            self.config = json.load(f)

        self.proxies = []
        ws = self.config["webshare"]

        # Add Swiss proxy
        ch = self.config["swiss"]
        self.proxies.append(Proxy(
            host=ch["host"], port=ch["port"],
            username=ch["username"], password=ch["password"],
            protocol=ch["protocol"], country=ch["country"],
            tags=ch["tags"]
        ))

        # Add Webshare proxies (per-proxy auth if present, else account-level)
        for p in self.config["proxies"]:
            self.proxies.append(Proxy(
                host=p["host"], port=p["port"],
                username=p.get("username", ws["username"]),
                password=p.get("password", ws["password"]),
                protocol=p.get("protocol", "http"), country=p.get("country", "??"),
                tags=p.get("tags", [])
            ))

        # Add free / no-auth proxies (harvested from public lists)
        for p in self.config.get("free_proxies", []):
            self.proxies.append(Proxy(
                host=p["host"], port=p["port"],
                username=p.get("username", ""), password=p.get("password", ""),
                protocol=p.get("protocol", "http"), country=p.get("country", "??"),
                tags=p.get("tags", ["scraping"]),
            ))

    def get(self, tag: str = None, country: str = None) -> Optional[Proxy]:
        """Get a random proxy matching filters."""
        candidates = self.proxies
        if tag:
            candidates = [p for p in candidates if tag in p.tags]
        if country:
            candidates = [p for p in candidates if p.country == country]
        return random.choice(candidates) if candidates else None

    def get_all(self, tag: str = None, country: str = None) -> list:
        """Get all proxies matching filters."""
        candidates = self.proxies
        if tag:
            candidates = [p for p in candidates if tag in p.tags]
        if country:
            candidates = [p for p in candidates if p.country == country]
        return candidates

    def get_url(self, tag: str = None, country: str = None) -> str:
        """Get proxy URL string."""
        p = self.get(tag=tag, country=country)
        return p.url if p else ""

    def get_requests_format(self, tag: str = None, country: str = None) -> dict:
        """Get proxy dict for requests library."""
        p = self.get(tag=tag, country=country)
        return p.requests_format if p else {}

    def get_for_ytdlp(self) -> str:
        """Get best proxy URL for yt-dlp."""
        p = self.get(tag="youtube")
        return p.url_socks5 if p.protocol == "socks5h" else p.url_http

    def get_for_n8n(self) -> dict:
        """Get proxy config for n8n HTTP Request node."""
        p = self.get(tag="scraping")
        return {
            "url": p.url_http,
            "host": p.host,
            "port": p.port,
            "username": p.username,
            "password": p.password
        }

    def rotate(self, tag: str = None) -> list:
        """Get all proxies for rotation."""
        return self.get_all(tag=tag)


# CLI usage
if __name__ == "__main__":
    import sys
    pool = ProxyPool()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        tag = sys.argv[2] if len(sys.argv) > 2 else None

        if cmd == "list":
            for p in pool.get_all(tag=tag):
                print(f"{p.country} | {p.url} | {p.tags}")
        elif cmd == "get":
            p = pool.get(tag=tag)
            print(p.url if p else "no proxy found")
        elif cmd == "youtube":
            print(pool.get_for_ytdlp())
        elif cmd == "n8n":
            print(json.dumps(pool.get_for_n8n(), indent=2))
        elif cmd == "test":
            import requests
            for p in pool.get_all(tag=tag):
                try:
                    r = requests.get("https://httpbin.org/ip",
                                     proxies=p.requests_format, timeout=10)
                    ip = r.json().get("origin", "?")
                    print(f"OK  {p.country} {p.host}:{p.port} → exit IP: {ip}")
                except Exception as e:
                    print(f"FAIL {p.country} {p.host}:{p.port} → {e.__class__.__name__}")
    else:
        print("Usage: proxy_pool.py [list|get|youtube|n8n|test] [tag]")
        print("Tags: youtube, scraping, osint, telegram, reliable")
        print(f"\nLoaded {len(pool.proxies)} proxies")
