import os
import re
import json
import requests

# =========================
# CONFIG
# =========================

BASE_DIR = os.getcwd()

LIVE_TV_DIR = os.path.join(BASE_DIR, "LiveTV")
os.makedirs(LIVE_TV_DIR, exist_ok=True)

MOVIE_JSON        = os.path.join(BASE_DIR, "all_movies.json")
OFFLINE_MOVIE_JSON = os.path.join(BASE_DIR, "offline movie.json")
OFFLINE_MOVIE_M3U  = os.path.join(BASE_DIR, "offline movie.m3u")

LIVE_TV_JSON  = os.path.join(LIVE_TV_DIR, "live_tv.json")
LIVE_TV_M3U   = os.path.join(LIVE_TV_DIR, "live_tv.m3u")
OFFLINE_TV_JSON = os.path.join(LIVE_TV_DIR, "offline Tv.json")
OFFLINE_TV_M3U  = os.path.join(LIVE_TV_DIR, "offline Tv.m3u")

# =========================
# RAW FILE LINKS
# =========================

URLS = [
    "https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/Bollywood/Movies.m3u",
    "https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/Bengali/Movies.m3u",
    "https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/Hollywood/Movies.m3u",
    "https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/WorldwideVOD/Movies.m3u",
    "https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/SouthIndian/Movies.m3u",
]

# =========================
# HELPER: #EXTINF parse করা
# =========================

def parse_extinf(line):
    """#EXTINF line থেকে name, logo, group বের করে"""
    name  = ""
    logo  = ""
    group = ""

    # tvg-logo="..." বের করো
    logo_match = re.search(r'tvg-logo="([^"]*)"', line)
    if logo_match:
        logo = logo_match.group(1)

    # group-title="..." বের করো
    group_match = re.search(r'group-title="([^"]*)"', line)
    if group_match:
        group = group_match.group(1)

    # শেষের comma-র পরের অংশ = name
    if "," in line:
        name = line.split(",", 1)[-1].strip()

    return name, logo, group

# =========================
# DOWNLOAD & PARSE M3U
# =========================

all_movies = []
all_tv     = []

for url in URLS:
    try:
        print(f"Downloading: {url}")
        r = requests.get(url, timeout=30)

        if r.status_code != 200:
            print(f"  ❌ HTTP {r.status_code} — skip")
            continue

        lines = r.text.splitlines()
        print(f"  ✅ {len(lines)} lines পাওয়া গেছে")

        current_info = None

        for line in lines:
            line = line.strip()

            if line.startswith("#EXTINF"):
                current_info = line

            elif line.startswith("http"):
                if current_info is None:
                    current_info = "#EXTINF:-1 ,Unknown"

                name, logo, group = parse_extinf(current_info)

                entry = {
                    "name":     name,
                    "logo":     logo,
                    "group":    group,
                    "url":      line,
                    "raw_info": current_info   # backup হিসেবে রাখা
                }

                # TV নাকি Movie — group বা name দিয়ে ঠিক করো
                lower = (name + " " + group).lower()
                is_tv = any(x in lower for x in ["tv", "news", "sports", "channel", "live"])

                if is_tv:
                    all_tv.append(entry)
                else:
                    all_movies.append(entry)

                current_info = None  # reset

    except Exception as e:
        print(f"  ❌ Error: {e}")

# =========================
# SAVE JSON
# =========================

# সব movie save করো (link check বাদ — stream URL HEAD/GET-এ fail করে)
with open(MOVIE_JSON, "w", encoding="utf-8") as f:
    json.dump(all_movies, f, indent=2, ensure_ascii=False)

# offline movie.json এ empty list (এখন link check নেই)
with open(OFFLINE_MOVIE_JSON, "w", encoding="utf-8") as f:
    json.dump([], f, indent=2, ensure_ascii=False)

# TV JSON
with open(LIVE_TV_JSON, "w", encoding="utf-8") as f:
    json.dump(all_tv, f, indent=2, ensure_ascii=False)

with open(OFFLINE_TV_JSON, "w", encoding="utf-8") as f:
    json.dump([], f, indent=2, ensure_ascii=False)

# =========================
# SAVE M3U
# =========================

def save_m3u(path, data):
    with open(path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for item in data:
            f.write(item["raw_info"] + "\n")
            f.write(item["url"] + "\n")

save_m3u(OFFLINE_MOVIE_M3U, [])   # empty
save_m3u(LIVE_TV_M3U,       all_tv)
save_m3u(OFFLINE_TV_M3U,    [])   # empty

# =========================
# DONE
# =========================

print("\n========================")
print("PROCESS COMPLETED")
print("========================")
print(f"Total Movies : {len(all_movies)}")
print(f"Total TV     : {len(all_tv)}")
print(f"all_movies.json → {MOVIE_JSON}")
