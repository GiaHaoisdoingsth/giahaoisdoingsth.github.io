#!/usr/bin/env python3
"""Download the DarlingnPlanner post photos into images/stories/.
Run from the repo root (next to index.html):
    python3 download_dnp_images.py          # only download
    python3 download_dnp_images.py --push   # download, then git add + commit + push
Needs only Python 3 and internet. Safe to re-run: existing files are skipped, so a second run only retries the missing ones.
NOTE: the Facebook image links in dnp-images.csv expire (around 6 Nov 2026). Run it before then."""
import csv, os, re, socket, subprocess, sys, time, urllib.request

DEST = os.path.join("images", "stories")
os.makedirs(DEST, exist_ok=True)

_orig = socket.getaddrinfo
MODE = {"v4": False}
def _gai(h, p, family=0, type=0, proto=0, flags=0):
    return _orig(h, p, socket.AF_INET if MODE["v4"] else family, type, proto, flags)
socket.getaddrinfo = _gai

def fetch(url, path, v4):
    MODE["v4"] = v4
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    if len(data) < 1000:
        raise ValueError("response too small")
    with open(path, "wb") as f:
        f.write(data)

def attempts(url):
    """Several ways to reach the same image: IPv4, then IPv6, then the same path on a regular IPv4 host."""
    alt = re.sub(r"^https://[^/]+", "https://scontent-phl2-1.xx.fbcdn.net", url)
    return [(url, True), (url, False), (alt, True)]

rows = list(csv.DictReader(open("dnp-images.csv", encoding="utf-8")))
ok = skipped = 0
failed = []
for i, r in enumerate(rows, 1):
    path = os.path.join(DEST, r["file"])
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        skipped += 1
    else:
        err = ""
        for url, v4 in attempts(r["url"]):
            try:
                fetch(url, path, v4); ok += 1; err = ""; break
            except Exception as e:
                err = str(e); time.sleep(0.5)
        if err:
            failed.append((r["file"], err))
    print(f"\r{i}/{len(rows)}", end="", flush=True)

print(f"\nDownloaded {ok}, already there {skipped}, failed {len(failed)}")
for f, e in failed:
    print("  FAILED", f, "-", e)
if failed:
    if any(("403" in e or "410" in e) for _, e in failed):
        print("Some links look expired (HTTP 403/410). Re-export the CSV from the scraper.")
    else:
        print("Network problem on this machine. Run this script again later, or on your own computer: it only retries the missing photos.")

if "--push" in sys.argv:
    paths = [DEST, "index.html", "dnp-posts.js", "dnp-images.csv", "download_dnp_images.py"]
    subprocess.run(["git", "add"] + [p for p in paths if os.path.exists(p)], check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode != 0:
        subprocess.run(["git", "commit", "-m", "Add DarlingnPlanner posts and photos"], check=True)
    subprocess.run(["git", "push"], check=True)
    print("Pushed to GitHub." + (" (without the missing photos above)" if failed else ""))
sys.exit(1 if failed else 0)
