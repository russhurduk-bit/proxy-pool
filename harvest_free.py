#!/usr/bin/env python3
"""Harvest free public HTTP proxies, validate them live, write working ones to config.json["free_proxies"].

Usage: python3 harvest_free.py [--target N] [--validate-url URL]
Default validates against https://api.ipify.org and keeps up to --target working proxies.
"""
import argparse
import concurrent.futures as cf
import json
import re
from pathlib import Path

import requests

CONFIG = Path(__file__).parent / "config.json"

SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
    "https://www.proxy-list.download/api/v1/get?type=http",
    "https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/main/http.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
]

_HOSTPORT = re.compile(r"(\d{1,3}(?:\.\d{1,3}){3}):(\d{2,5})")


def fetch_candidates() -> set:
    cands = set()
    for url in SOURCES:
        try:
            r = requests.get(url, timeout=20)
            if r.status_code != 200:
                print(f"  src {r.status_code} {url[:60]}")
                continue
            found = _HOSTPORT.findall(r.text)
            for host, port in found:
                cands.add((host, int(port)))
            print(f"  +{len(found):>5} from {url[:60]}")
        except Exception as e:
            print(f"  ERR {e.__class__.__name__} {url[:60]}")
    return cands


def validate(hostport, target: str, timeout: float = 6.0):
    host, port = hostport
    proxies = {"http": f"http://{host}:{port}", "https": f"http://{host}:{port}"}
    try:
        r = requests.get(target, proxies=proxies, timeout=timeout)
        if r.status_code == 200:
            return hostport
    except Exception:
        return None
    return None


_IG_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "X-IG-App-ID": "936619743392459",
    "X-ASBD-ID": "129477",
    "X-IG-WWW-Claim": "0",
}
_IG_PROBE = "https://www.instagram.com/api/v1/feed/user/instagram/username/?count=3"


def validate_ig(hostport, timeout: float = 12.0):
    """Return hostport if the proxy can reach IG feed API (passes IG auth wall)."""
    host, port = hostport
    proxies = {"http": f"http://{host}:{port}", "https": f"http://{host}:{port}"}
    try:
        r = requests.get(_IG_PROBE, headers=_IG_HEADERS, proxies=proxies, timeout=timeout)
        if r.status_code == 200 and r.json().get("user", {}).get("pk"):
            return hostport
    except Exception:
        return None
    return None


def harvest(target: int = 40, validate_url: str = "https://api.ipify.org",
            workers: int = 200, verbose: bool = True) -> int:
    """Harvest + validate free proxies, write working ones to config. Returns count kept."""
    def say(m):
        if verbose:
            print(m)

    say("Fetching candidate lists...")
    cands = fetch_candidates()
    say(f"Total unique candidates: {len(cands)}")

    say(f"Validating against {validate_url} ({workers} workers)...")
    working = []
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(validate, c, validate_url): c for c in cands}
        for fut in cf.as_completed(futs):
            res = fut.result()
            if res:
                working.append(res)
                say(f"  OK {res[0]}:{res[1]}  ({len(working)})")
                if len(working) >= target:
                    for f in futs:
                        f.cancel()
                    break

    if not working:
        say("No working proxies found — keeping existing config untouched.")
        return 0

    # Stage 2: among live proxies, find which can pass Instagram's auth wall.
    say(f"Probing {len(working)} live proxies against Instagram...")
    ig_ok = set()
    with cf.ThreadPoolExecutor(max_workers=min(50, len(working))) as ex:
        for res in ex.map(lambda c: validate_ig(c), working):
            if res:
                ig_ok.add(res)
                say(f"  IG OK {res[0]}:{res[1]}  ({len(ig_ok)})")
    say(f"IG-capable proxies: {len(ig_ok)}/{len(working)}")

    cfg = json.load(open(CONFIG))
    free = []
    for h, p in working:
        tags = ["scraping", "youtube", "osint", "telegram"]
        if (h, p) in ig_ok:
            tags.append("instagram")
        free.append({"host": h, "port": p, "username": "", "password": "",
                     "protocol": "http", "country": "??", "tags": tags})
    # IG-capable first so consumers that pick the first match prefer them
    free.sort(key=lambda x: "instagram" not in x["tags"])
    cfg["free_proxies"] = free
    json.dump(cfg, open(CONFIG, "w"), indent=2, ensure_ascii=False)
    say(f"Wrote {len(free)} free proxies ({len(ig_ok)} IG-capable) to {CONFIG}")
    return len(free)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=50, help="how many live proxies to keep")
    ap.add_argument("--validate-url", default="https://api.ipify.org")
    ap.add_argument("--workers", type=int, default=200)
    args = ap.parse_args()
    harvest(target=args.target, validate_url=args.validate_url, workers=args.workers)


if __name__ == "__main__":
    main()
