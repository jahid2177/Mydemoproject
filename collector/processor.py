import os
import json
import requests
from concurrent.futures import ThreadPoolExecutor

# =========================
# CONFIG
# =========================

BASE_DIR = os.getcwd()

LIVE_TV_DIR = os.path.join(BASE_DIR, "LiveTV")
os.makedirs(LIVE_TV_DIR, exist_ok=True)

MOVIE_JSON = os.path.join(BASE_DIR, "all_movies.json")
OFFLINE_MOVIE_JSON = os.path.join(BASE_DIR, "ofline movie.json")
OFFLINE_MOVIE_M3U = os.path.join(BASE_DIR, "ofline movie.m3u")

LIVE_TV_JSON = os.path.join(LIVE_TV_DIR, "live_tv.json")
LIVE_TV_M3U = os.path.join(LIVE_TV_DIR, "live_tv.m3u")
OFFLINE_TV_JSON = os.path.join(LIVE_TV_DIR, "ofline Tv.json")
OFFLINE_TV_M3U = os.path.join(LIVE_TV_DIR, "ofline Tv.m3u")

# =========================
# RAW FILE LINKS
# =========================

URLS = [
    "https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/Bollywood/Movies.m3u",
    "https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/Bengali/Movies.m3u",
    "https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/Hollywood/Movies.m3u",
    "https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/WorldwideVOD/Movies.m3u",
]

# =========================
# DOWNLOAD FILES
# =========================

all_lines = []

for url in URLS:
    try:
        print(f"Downloading: {url}")
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            all_lines.extend(r.text.splitlines())
    except Exception as e:
        print(e)

# =========================
# PARSE M3U
# =========================

entries = []
current_info = None

for line in all_lines:
    line = line.strip()

    if line.startswith("#EXTINF"):
        current_info = line

    elif line.startswith("http"):
        entries.append({
            "info": current_info,
            "url": line
        })

# =========================
# LINK CHECKER
# =========================

def is_online(url):
    try:
        r = requests.head(url, timeout=10, allow_redirects=True)
        if r.status_code < 400:
            return True

        r = requests.get(url, stream=True, timeout=10)
        return r.status_code < 400

    except:
        return False

# =========================
# CHECK LINKS
# =========================

online_movies = []
offline_movies = []

online_tv = []
offline_tv = []


def process(entry):
    info = entry["info"] or ""
    url = entry["url"]

    online = is_online(url)

    lower = info.lower()

    is_tv = any(x in lower for x in [
        "tv",
        "news",
        "sports",
        "channel",
        "live"
    ])

    if is_tv:
        if online:
            online_tv.append(entry)
        else:
            offline_tv.append(entry)
    else:
        if online:
            online_movies.append(entry)
        else:
            offline_movies.append(entry)


with ThreadPoolExecutor(max_workers=20) as executor:
    executor.map(process, entries)

# =========================
# SAVE JSON
# =========================

with open(MOVIE_JSON, "w", encoding="utf-8") as f:
    json.dump(online_movies, f, indent=4, ensure_ascii=False)

with open(OFFLINE_MOVIE_JSON, "w", encoding="utf-8") as f:
    json.dump(offline_movies, f, indent=4, ensure_ascii=False)

with open(LIVE_TV_JSON, "w", encoding="utf-8") as f:
    json.dump(online_tv, f, indent=4, ensure_ascii=False)

with open(OFFLINE_TV_JSON, "w", encoding="utf-8") as f:
    json.dump(offline_tv, f, indent=4, ensure_ascii=False)

# =========================
# SAVE M3U
# =========================

def save_m3u(path, data):
    with open(path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for item in data:
            if item["info"]:
                f.write(item["info"] + "\n")
            f.write(item["url"] + "\n")

save_m3u(LIVE_TV_M3U, online_tv)
save_m3u(OFFLINE_TV_M3U, offline_tv)
save_m3u(OFFLINE_MOVIE_M3U, offline_movies)

# =========================
# DONE
# =========================

print("\n========================")
print("PROCESS COMPLETED")
print("========================")
print(f"Online Movies : {len(online_movies)}")
print(f"Offline Movies: {len(offline_movies)}")
print(f"Online TV     : {len(online_tv)}")
print(f"Offline TV    : {len(offline_tv)}")
