import json
import requests
from concurrent.futures import ThreadPoolExecutor

SOURCES = [
    "https://raw.githubusercontent.com/time2shine/IPTV/refs/heads/master/scripts/static_movies(103.225.94.27).json",
    "https://raw.githubusercontent.com/time2shine/IPTV/refs/heads/master/scripts/static_movies(cinehub24).json",
    "https://raw.githubusercontent.com/time2shine/IPTV/refs/heads/master/scripts/static_movies(ctgfun).json",
    "https://raw.githubusercontent.com/time2shine/IPTV/refs/heads/master/scripts/static_movies(discoveryftp).json"
]

movies = []
duplicate_movies = []
offline_movies = []

seen_links = set()


def extract_link(item):
    keys = [
        "url",
        "link",
        "stream_url",
        "video_url",
        "file",
        "source"
    ]

    for key in keys:
        if key in item and isinstance(item[key], str):
            return item[key]

    return None


def is_online(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.head(
            url,
            headers=headers,
            timeout=10,
            allow_redirects=True
        )

        if response.status_code < 400:
            return True

        response = requests.get(
            url,
            headers=headers,
            timeout=10,
            stream=True,
            allow_redirects=True
        )

        return response.status_code < 400

    except:
        return False


def process_movie(item):
    link = extract_link(item)

    if not link:
        return

    if link in seen_links:
        duplicate_movies.append(item)
        return

    if not is_online(link):
        offline_movies.append(item)
        return

    seen_links.add(link)
    movies.append(item)


for source in SOURCES:
    try:
        print(f"Fetching: {source}")

        response = requests.get(source, timeout=30)
        response.raise_for_status()

        data = response.json()

        if isinstance(data, dict):
            data = data.get("movies", [])

        if not isinstance(data, list):
            continue

        with ThreadPoolExecutor(max_workers=20) as executor:
            executor.map(process_movie, data)

    except Exception as e:
        print(f"Source Error: {e}")


with open("movies_link.json", "w", encoding="utf-8") as f:
    json.dump(movies, f, indent=4, ensure_ascii=False)

with open("duplicate_link.json", "w", encoding="utf-8") as f:
    json.dump(duplicate_movies, f, indent=4, ensure_ascii=False)

with open("offline_link.json", "w", encoding="utf-8") as f:
    json.dump(offline_movies, f, indent=4, ensure_ascii=False)

print("Done")
print(f"Movies: {len(movies)}")
print(f"Duplicate: {len(duplicate_movies)}")
print(f"Offline: {len(offline_movies)}")with open("duplicate_link.json", "w", encoding="utf-8") as f:
    json.dump(duplicate_movies, f, indent=4, ensure_ascii=False)

with open("offline_link.json", "w", encoding="utf-8") as f:
    json.dump(offline_movies, f, indent=4, ensure_ascii=False)


print("Done")
print(f"All Movies: {len(all_movies)}")
print(f"Duplicate: {len(duplicate_movies)}")
print(f"Offline: {len(offline_movies)}")
