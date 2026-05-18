from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlparse, quote

import aiohttp
import requests

# =========================
# CONFIG
# =========================

BASE_DIR = Path(__file__).resolve().parent
LIVE_TV_DIR = BASE_DIR / "LiveTV"
MOVIES_DIR = BASE_DIR / "Movies"
ASSETS_DIR = BASE_DIR / "assets" / "logos"

DEFAULT_LOGO = str((ASSETS_DIR / "default-logo.png").as_posix())
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "").strip()

REQUEST_TIMEOUT = 12
CONCURRENCY = 20
USER_AGENT = "Mozilla/5.0 (GitHubActions IPTV Bot)"

# আপনার আগের raw links রাখা হলো
PLAYLIST_SOURCES = [
    "https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/Bollywood/Movies.m3u",
    "https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/Bengali/Movies.m3u",
    "https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/Hollywood/Movies.m3u",
    "https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/WorldwideVOD/Movies.m3u",
    "https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/SouthIndian/Movies.m3u",
]

MOVIE_CATEGORIES = ["Bollywood", "Bengali", "Hollywood", "SouthIndian", "WorldwideVOD"]


# =========================
# PATH SETUP
# =========================

def ensure_dirs() -> None:
    LIVE_TV_DIR.mkdir(parents=True, exist_ok=True)
    MOVIES_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    for category in MOVIE_CATEGORIES:
        (MOVIES_DIR / category).mkdir(parents=True, exist_ok=True)


# =========================
# HELPERS
# =========================

def safe_attr(value: str) -> str:
    return str(value or "").replace('"', "'").strip()


def normalize_url(url: str) -> str:
    return (url or "").strip()


def detect_quality(text: str) -> str:
    t = (text or "").lower()
    if any(x in t for x in ["2160", "4k", "uhd"]):
        return "4K"
    if any(x in t for x in ["1080", "fhd", "fullhd"]):
        return "1080p"
    if any(x in t for x in ["720", "hd"]):
        return "720p"
    if any(x in t for x in ["480", "sd"]):
        return "SD"
    return "Unknown"


def parse_attrs(extinf_line: str) -> Dict[str, str]:
    return dict(re.findall(r'([\w\-]+)="([^"]*)"', extinf_line))


def parse_name(extinf_line: str, attrs: Dict[str, str]) -> str:
    if "," in extinf_line:
        return extinf_line.split(",", 1)[1].strip()
    return attrs.get("tvg-name") or "Unknown"


def is_tv_item(name: str, group: str) -> bool:
    hay = f"{name} {group}".lower()
    tv_keywords = [
        "tv", "channel", "news", "sports", "live", "music", "kids",
        "bangla tv", "star jalsha", "zee", "sony", "discovery", "nat geo"
    ]
    return any(k in hay for k in tv_keywords)


def infer_movie_category(item: Dict) -> str:
    hay = f"{item.get('group','')} {item.get('source','')} {item.get('name','')}".lower()

    if "bollywood" in hay:
        return "Bollywood"
    if "bengali" in hay or "bangla" in hay:
        return "Bengali"
    if "hollywood" in hay:
        return "Hollywood"
    if "southindian" in hay or "south indian" in hay or "tamil" in hay or "telugu" in hay or "malayalam" in hay:
        return "SouthIndian"
    return "WorldwideVOD"


def item_to_extinf(item: Dict) -> str:
    attrs = [
        f'tvg-id="{safe_attr(item.get("tvg_id", ""))}"',
        f'tvg-name="{safe_attr(item.get("name", ""))}"',
        f'tvg-logo="{safe_attr(item.get("logo", ""))}"',
        f'group-title="{safe_attr(item.get("group", "Other"))}"',
    ]
    return f'#EXTINF:-1 {" ".join(attrs)},{safe_attr(item.get("name", "Unknown"))}'


def remove_duplicates(items: List[Dict]) -> List[Dict]:
    seen = set()
    result = []
    for item in items:
        key = normalize_url(item.get("url", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def auto_logo(item: Dict) -> str:
    if item.get("logo"):
        return item["logo"]

    parsed = urlparse(item.get("url", ""))
    host = parsed.hostname or ""
    if host and "." in host:
        return f"https://logo.clearbit.com/{host}"

    return DEFAULT_LOGO


def fetch_tmdb_poster(title: str) -> str:
    if not TMDB_API_KEY:
        return ""

    try:
        url = "https://api.themoviedb.org/3/search/movie"
        params = {"api_key": TMDB_API_KEY, "query": title}
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        results = data.get("results", [])
        if not results:
            return ""
        poster_path = results[0].get("poster_path")
        if not poster_path:
            return ""
        return f"https://image.tmdb.org/t/p/w500{poster_path}"
    except Exception:
        return ""


# =========================
# M3U PARSING
# =========================

def parse_m3u_text(text: str, source_name: str) -> Tuple[List[Dict], List[str]]:
    items: List[Dict] = []
    epg_urls: List[str] = []

    current_extinf = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("#EXTM3U"):
            header_attrs = parse_attrs(line)
            epg = header_attrs.get("x-tvg-url", "").strip()
            if epg:
                for url in re.split(r"[,\s]+", epg):
                    if url.strip():
                        epg_urls.append(url.strip())
            continue

        if line.startswith("#EXTINF"):
            current_extinf = line
            continue

        if line.startswith("#"):
            continue

        if re.match(r"^(https?|rtmp|rtsp|udp)://", line, re.I):
            if current_extinf is None:
                current_extinf = "#EXTINF:-1,Unknown"

            attrs = parse_attrs(current_extinf)
            name = parse_name(current_extinf, attrs)
            group = attrs.get("group-title", "Other")

            items.append({
                "name": name,
                "group": group or "Other",
                "url": line,
                "logo": attrs.get("tvg-logo", ""),
                "tvg_id": attrs.get("tvg-id", ""),
                "quality": detect_quality(f"{name} {group} {line}"),
                "source": source_name,
                "raw_info": current_extinf,
            })
            current_extinf = None

    return items, epg_urls


# =========================
# ASYNC FETCH + VALIDATION
# =========================

async def fetch_text(session: aiohttp.ClientSession, source: str) -> str:
    if source.startswith("http://") or source.startswith("https://"):
        async with session.get(
            source,
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            headers={"User-Agent": USER_AGENT},
            ssl=False,
        ) as resp:
            resp.raise_for_status()
            return await resp.text(errors="ignore")

    return Path(source).read_text(encoding="utf-8", errors="ignore")


async def fetch_all_sources(sources: List[str]) -> Tuple[List[Dict], List[str]]:
    all_items: List[Dict] = []
    all_epg: List[str] = []

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_text(session, src) for src in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for source, result in zip(sources, results):
        if isinstance(result, Exception):
            print(f"[ERROR] source failed: {source} -> {result}")
            continue

        items, epg_urls = parse_m3u_text(result, source)
        all_items.extend(items)
        all_epg.extend(epg_urls)

    return all_items, sorted(set(all_epg))


async def validate_streams(items: List[Dict]) -> List[Dict]:
    sem = asyncio.Semaphore(CONCURRENCY)

    async def probe(item: Dict, session: aiohttp.ClientSession) -> Dict:
        url = item.get("url", "")
        lower_url = url.lower()

        async with sem:
            try:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                    headers={"User-Agent": USER_AGENT, "Range": "bytes=0-1024"},
                    allow_redirects=True,
                    ssl=False,
                ) as resp:
                    ok = 200 <= resp.status < 400
                    hls_valid = True

                    if ".m3u8" in lower_url:
                        body = await resp.text(errors="ignore")
                        hls_valid = "#EXTM3U" in body

                    item["alive"] = ok and hls_valid
                    item["hls_valid"] = hls_valid
                    return item
            except Exception:
                item["alive"] = False
                item["hls_valid"] = False
                return item

    async with aiohttp.ClientSession() as session:
        tasks = [probe(item, session) for item in items]
        return await asyncio.gather(*tasks)


# =========================
# XTREAM SUPPORT (OPTIONAL)
# GitHub Secret: XTREAM_CONFIG_JSON
# Example:
# [{"server":"http://example.com:8080","username":"u","password":"p"}]
# =========================

def load_xtream_items() -> List[Dict]:
    raw = os.getenv("XTREAM_CONFIG_JSON", "").strip()
    if not raw:
        return []

    try:
        configs = json.loads(raw)
    except Exception:
        print("[WARN] XTREAM_CONFIG_JSON invalid")
        return []

    items: List[Dict] = []

    for conf in configs:
        server = str(conf.get("server", "")).rstrip("/")
        username = conf.get("username", "")
        password = conf.get("password", "")

        if not server or not username or not password:
            continue

        endpoints = [
            ("get_live_streams", "live"),
            ("get_vod_streams", "movie"),
        ]

        for action, mode in endpoints:
            try:
                api_url = f"{server}/player_api.php?username={username}&password={password}&action={action}"
                r = requests.get(api_url, timeout=20)
                r.raise_for_status()
                rows = r.json()

                for row in rows:
                    stream_id = row.get("stream_id")
                    if not stream_id:
                        continue

                    if mode == "live":
                        ext = row.get("container_extension") or "m3u8"
                        stream_url = f"{server}/live/{username}/{password}/{stream_id}.{ext}"
                    else:
                        ext = row.get("container_extension") or "mp4"
                        stream_url = f"{server}/movie/{username}/{password}/{stream_id}.{ext}"

                    name = row.get("name") or f"{mode}-{stream_id}"
                    group = row.get("category_name") or ("Live TV" if mode == "live" else "Xtream Movies")

                    items.append({
                        "name": name,
                        "group": group,
                        "url": stream_url,
                        "logo": row.get("stream_icon", ""),
                        "tvg_id": "",
                        "quality": detect_quality(f"{name} {group} {stream_url}"),
                        "source": f"xtream:{server}",
                        "raw_info": "",
                    })
            except Exception as e:
                print(f"[WARN] Xtream fetch failed from {server} ({action}): {e}")

    return items


# =========================
# SAVE FILES
# =========================

def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_m3u(path: Path, items: List[Dict], epg_urls: List[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    header = "#EXTM3U"
    if epg_urls:
        header += f' x-tvg-url="{",".join(epg_urls)}"'

    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n")
        for item in items:
            f.write(item_to_extinf(item) + "\n")
            f.write(item["url"] + "\n")


def simplified_android_json(items: List[Dict]) -> List[Dict]:
    return [
        {
            "name": item.get("name", ""),
            "category": item.get("group", "Other"),
            "url": item.get("url", ""),
            "logo": item.get("logo", ""),
            "poster": item.get("poster", ""),
            "quality": item.get("quality", "Unknown"),
        }
        for item in items
    ]


# =========================
# MAIN
# =========================

async def main() -> None:
    ensure_dirs()

    print("[INFO] Fetching playlists...")
    playlist_items, epg_urls = await fetch_all_sources(PLAYLIST_SOURCES)

    print("[INFO] Loading Xtream (optional)...")
    xtream_items = load_xtream_items()

    all_items = playlist_items + xtream_items
    all_items = remove_duplicates(all_items)

    for item in all_items:
        item["logo"] = auto_logo(item)

    print(f"[INFO] Total merged items before validation: {len(all_items)}")

    print("[INFO] Validating streams asynchronously...")
    validated_items = await validate_streams(all_items)

    alive_items = [x for x in validated_items if x.get("alive")]
    dead_items = [x for x in validated_items if not x.get("alive")]

    for item in alive_items:
        if not is_tv_item(item.get("name", ""), item.get("group", "")):
            item["poster"] = fetch_tmdb_poster(item["name"])

    live_tv = []
    offline_tv = []
    all_movies = []
    offline_movies = []

    for item in alive_items:
        if is_tv_item(item.get("name", ""), item.get("group", "")):
            live_tv.append(item)
        else:
            item["category"] = infer_movie_category(item)
            all_movies.append(item)

    for item in dead_items:
        if is_tv_item(item.get("name", ""), item.get("group", "")):
            offline_tv.append(item)
        else:
            item["category"] = infer_movie_category(item)
            offline_movies.append(item)

    # sort by group + name
    live_tv.sort(key=lambda x: (x.get("group", "").lower(), x.get("name", "").lower()))
    offline_tv.sort(key=lambda x: (x.get("group", "").lower(), x.get("name", "").lower()))
    all_movies.sort(key=lambda x: (x.get("category", "").lower(), x.get("name", "").lower()))
    offline_movies.sort(key=lambda x: (x.get("category", "").lower(), x.get("name", "").lower()))

    # Root/LiveTV outputs
    save_json(BASE_DIR / "all_movies.json", all_movies)
    save_json(BASE_DIR / "ofline movie.json", offline_movies)
    save_json(LIVE_TV_DIR / "live_tv.json", live_tv)
    save_json(LIVE_TV_DIR / "ofline Tv.json", offline_tv)
    save_json(LIVE_TV_DIR / "epg_sources.json", epg_urls)

    save_m3u(BASE_DIR / "ofline movie.m3u", offline_movies)
    save_m3u(LIVE_TV_DIR / "live_tv.m3u", live_tv, epg_urls=epg_urls)
    save_m3u(LIVE_TV_DIR / "ofline Tv.m3u", offline_tv, epg_urls=epg_urls)

    # Category-wise movie outputs
    for category in MOVIE_CATEGORIES:
        category_items = [x for x in all_movies if x.get("category") == category]
        category_dir = MOVIES_DIR / category

        save_json(category_dir / "Movies.json", category_items)
        save_json(category_dir / "Movies_app.json", simplified_android_json(category_items))
        save_m3u(category_dir / "Movies.m3u", category_items)

    print("===================================")
    print("[DONE] IPTV processing completed")
    print(f"[DONE] Alive items   : {len(alive_items)}")
    print(f"[DONE] Dead items    : {len(dead_items)}")
    print(f"[DONE] Movies        : {len(all_movies)}")
    print(f"[DONE] Live TV       : {len(live_tv)}")
    print(f"[DONE] EPG sources   : {len(epg_urls)}")
    print("===================================")


if __name__ == "__main__":
    asyncio.run(main())
