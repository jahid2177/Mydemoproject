import json
import os
import requests
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import pytz

DHAKA_TZ = pytz.timezone('Asia/Dhaka')

SOURCES = [
    "https://raw.githubusercontent.com/time2shine/IPTV/refs/heads/master/scripts/static_movies(103.225.94.27).json",
    "https://raw.githubusercontent.com/time2shine/IPTV/refs/heads/master/scripts/static_movies(cinehub24).json",
    "https://raw.githubusercontent.com/time2shine/IPTV/refs/heads/master/scripts/static_movies(ctgfun).json",
    "https://raw.githubusercontent.com/time2shine/IPTV/refs/heads/master/scripts/static_movies(discoveryftp).json",
]

SOURCE_NAMES = {
    "103.225.94.27": "103.225.94.27",
    "cinehub24":     "cinehub24.com",
    "ctgfun":        "ctgfun",
    "discoveryftp":  "discoveryftp",
}

merged = []
seen_links = set()
lock = threading.Lock()

source_stats = {}


def get_source_name(url):
    for key, name in SOURCE_NAMES.items():
        if key in url:
            return name
    return url


def extract_items(data, source_url):
    items = []
    if isinstance(data, dict):
        extracted = data.get("movies", data.get("data", data.get("Movies", None)))
        if extracted is not None:
            data = extracted
        else:
            for title, movie in data.items():
                if isinstance(movie, dict) and "links" in movie:
                    for link_obj in movie["links"]:
                        if isinstance(link_obj, dict):
                            link_obj["title"] = title
                            link_obj["_source_name"] = get_source_name(source_url)
                            items.append(link_obj)
            return items

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                item["_source_name"] = get_source_name(source_url)
            items.append(item)
    return items


def get_url(item):
    if isinstance(item, str) and item.startswith("http"):
        return item
    if isinstance(item, dict):
        item_lower = {str(k).lower(): v for k, v in item.items()}
        for key in ["url", "link", "stream_url", "video_url", "file", "movie_url", "path", "stream"]:
            if key in item_lower and isinstance(item_lower[key], str):
                val = item_lower[key]
                if val.startswith("http"):
                    return val
    return None


def process_item(item):
    url = get_url(item)
    if not url:
        return "skipped"
    with lock:
        if url in seen_links:
            return "duplicate"
        seen_links.add(url)
        merged.append(item)
        return "added"


for source_url in SOURCES:
    source_name = get_source_name(source_url)
    print(f"\nFetching: {source_name} ...")
    try:
        resp = requests.get(source_url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        items = extract_items(data, source_url)

        if not items:
            print(f"  Warning: 0 items found. Skipping.")
            source_stats[source_name] = {"fetched": 0, "added": 0, "duplicate": 0, "skipped": 0}
            continue

        print(f"  Fetched: {len(items)} items")

        added = duplicate = skipped = 0
        with ThreadPoolExecutor(max_workers=20) as ex:
            results = list(ex.map(process_item, items))

        for r in results:
            if r == "added":      added += 1
            elif r == "duplicate": duplicate += 1
            else:                  skipped += 1

        source_stats[source_name] = {
            "fetched":   len(items),
            "added":     added,
            "duplicate": duplicate,
            "skipped":   skipped,
        }
        print(f"  Added: {added}  |  Duplicate: {duplicate}  |  Skipped: {skipped}")

    except requests.exceptions.RequestException as e:
        print(f"  Network Error: {e}")
        source_stats[source_name] = {"fetched": 0, "added": 0, "duplicate": 0, "skipped": 0, "error": str(e)}
    except Exception as e:
        print(f"  Unexpected Error: {e}")
        source_stats[source_name] = {"fetched": 0, "added": 0, "duplicate": 0, "skipped": 0, "error": str(e)}

print("\n---------------------------------")
print("Saving merge_link.json ...")

with open("merge_link.json", "w", encoding="utf-8") as f:
    json.dump(merged, f, indent=4, ensure_ascii=False)

print(f"Done! Total unique movies: {len(merged)}")

os.makedirs("logs", exist_ok=True)

now_dhaka = datetime.now(timezone.utc).astimezone(DHAKA_TZ)
report_lines = [
    "=" * 50,
    "  MERGE REPORT — merge_link.json",
    "=" * 50,
    f"  Generated : {now_dhaka.strftime('%Y-%m-%d %H:%M:%S +0600 (Dhaka)')}",
    f"  Total unique movies : {len(merged)}",
    "",
    "  Per-source breakdown:",
    "-" * 50,
]

total_fetched = total_added = total_dup = total_skip = 0
for sname, stats in source_stats.items():
    report_lines.append(f"  Source : {sname}")
    report_lines.append(f"    Fetched   : {stats.get('fetched', 0)}")
    report_lines.append(f"    Added     : {stats.get('added', 0)}")
    report_lines.append(f"    Duplicate : {stats.get('duplicate', 0)}")
    report_lines.append(f"    Skipped   : {stats.get('skipped', 0)}")
    if "error" in stats:
        report_lines.append(f"    Error     : {stats['error']}")
    report_lines.append("")
    total_fetched += stats.get("fetched", 0)
    total_added   += stats.get("added", 0)
    total_dup     += stats.get("duplicate", 0)
    total_skip    += stats.get("skipped", 0)

report_lines += [
    "-" * 50,
    f"  TOTAL Fetched   : {total_fetched}",
    f"  TOTAL Added     : {total_added}",
    f"  TOTAL Duplicate : {total_dup}",
    f"  TOTAL Skipped   : {total_skip}",
    "=" * 50,
]

report_text = "\n".join(report_lines) + "\n"
with open("logs/merge_link.txt", "w", encoding="utf-8") as f:
    f.write(report_text)

print(report_text)
