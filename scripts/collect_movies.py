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
    # ১. ডেটা যদি সরাসরি লিংক (String) হয়
    if isinstance(item, str):
        if item.startswith("http"):
            return item
        return None
        
    # ২. ডেটা যদি ডিকশনারি (Dict) হয়
    if isinstance(item, dict):
        # Key গুলোকে case-insensitive করার জন্য সব ছোট হাতের করে নিচ্ছি
        item_lower = {str(k).lower(): v for k, v in item.items()}
        
        # খোঁজার জন্য সম্ভাব্য সব রকম নামের লিস্ট
        keys = ["url", "link", "stream_url", "video_url", "file", "source", "movie_url", "path", "stream"]

        for key in keys:
            if key in item_lower and isinstance(item_lower[key], str):
                return item_lower[key]

    return None

def is_online(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        if response.status_code < 400:
            return True
            
        response = requests.get(url, headers=headers, timeout=10, stream=True, allow_redirects=True)
        return response.status_code < 400
    except:
        return False

def process_movie(item):
    link = extract_link(item)

    if not link:
        # লিংক না পেলে কনসোলে প্রিন্ট করবে, যাতে আপনি বুঝতে পারেন ডেটার স্ট্রাকচার কেমন
        print(f"Skipped (No valid link found): {item}")
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
        print(f"\nFetching: {source}")
        response = requests.get(source, timeout=30)
        response.raise_for_status()

        data = response.json()

        if isinstance(data, dict):
            # যদি 'movies' না থাকে, তবে 'data' বা অন্য কোনো key ট্রাই করবে
            data = data.get("movies", data.get("data", data.get("Movies", [])))

        if not isinstance(data, list) or len(data) == 0:
            print("Warning: Data is empty or not a list. Skipping this source.")
            continue
            
        print(f"Success: Found {len(data)} items to process in this source.")

        with ThreadPoolExecutor(max_workers=20) as executor:
            # list() ব্যবহার করা হয়েছে যাতে থ্রেডের ভেতরের কোনো এরর লুকিয়ে না থাকে
            list(executor.map(process_movie, data))

    except requests.exceptions.RequestException as e:
        print(f"Network Error for this source: {e}")
    except json.JSONDecodeError:
        print(f"JSON Error: This source does not contain valid JSON data.")
    except Exception as e:
        print(f"Unexpected Error: {e}")

print("\n---------------------------------")
print("Saving Files...")

with open("movies_link.json", "w", encoding="utf-8") as f:
    json.dump(movies, f, indent=4, ensure_ascii=False)

with open("duplicate_link.json", "w", encoding="utf-8") as f:
    json.dump(duplicate_movies, f, indent=4, ensure_ascii=False)

with open("offline_link.json", "w", encoding="utf-8") as f:
    json.dump(offline_movies, f, indent=4, ensure_ascii=False)

print("Done")
print(f"Movies: {len(movies)}")
print(f"Duplicate: {len(duplicate_movies)}")
print(f"Offline: {len(offline_movies)}")
