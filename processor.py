import os
from collections import Counter

import requests

from core.duplicate_remover import remove_duplicates
from core.logo_fetcher import apply_logos
from core.playlist_utils import classify_entry, discover_local_playlists, parse_m3u_text, write_json, write_m3u

BASE_DIR = os.getcwd()
LIVE_TV_DIR = os.path.join(BASE_DIR, 'LiveTV')
os.makedirs(LIVE_TV_DIR, exist_ok=True)

MOVIE_JSON = os.path.join(BASE_DIR, 'all_movies.json')
OFFLINE_MOVIE_JSON = os.path.join(BASE_DIR, 'offline_movie.json')
OFFLINE_MOVIE_M3U = os.path.join(BASE_DIR, 'offline_movie.m3u')
LIVE_TV_JSON = os.path.join(LIVE_TV_DIR, 'live_tv.json')
LIVE_TV_M3U = os.path.join(LIVE_TV_DIR, 'live_tv.m3u')
OFFLINE_TV_JSON = os.path.join(LIVE_TV_DIR, 'offline_tv.json')
OFFLINE_TV_M3U = os.path.join(LIVE_TV_DIR, 'offline_tv.m3u')
REPORT = os.path.join(BASE_DIR, 'logs', 'processor_report.txt')

REMOTE_URLS = [
    'https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/Bollywood/Movies.m3u',
    'https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/Bengali/Movies.m3u',
    'https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/Hollywood/Movies.m3u',
    'https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/WorldwideVOD/Movies.m3u',
    'https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/SouthIndian/Movies.m3u',
]

CHECK_TIMEOUT = 8  # seconds for online/offline check


def load_remote_playlist(url):
    try:
        response = requests.get(url, timeout=25, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            return parse_m3u_text(response.text, source=url)[0]
        print(f'Skip remote {url} -> HTTP {response.status_code}')
    except Exception as exc:
        print(f'Skip remote {url} -> {exc}')
    return []


def is_online(url):
    """Check if a stream URL is reachable (HEAD or GET)."""
    try:
        r = requests.head(url, timeout=CHECK_TIMEOUT, headers={'User-Agent': 'Mozilla/5.0'}, allow_redirects=True)
        if r.status_code < 400:
            return True
        # fallback to GET for servers that reject HEAD
        r = requests.get(url, timeout=CHECK_TIMEOUT, headers={'User-Agent': 'Mozilla/5.0'}, stream=True)
        return r.status_code < 400
    except Exception:
        return False


def split_online_offline(entries):
    """Split entries into online and offline lists by checking each URL."""
    online, offline = [], []
    total = len(entries)
    for i, entry in enumerate(entries, 1):
        url = entry.get('url', '')
        if not url:
            offline.append(entry)
            continue
        status = is_online(url)
        print(f'  [{i}/{total}] {"✓ online" if status else "✗ offline"}  {url[:80]}')
        (online if status else offline).append(entry)
    return online, offline


def load_all_entries():
    local_files = [path for path in discover_local_playlists(BASE_DIR) if os.path.basename(path) == 'Movies.m3u']
    raw_entries = []
    if local_files:
        for path in local_files:
            with open(path, 'r', encoding='utf-8', errors='ignore') as handle:
                raw_entries.extend(parse_m3u_text(handle.read(), source=path)[0])
    else:
        for url in REMOTE_URLS:
            raw_entries.extend(load_remote_playlist(url))

    before_count = len(raw_entries)
    entries = remove_duplicates(apply_logos(raw_entries))
    after_count = len(entries)
    print(f'Duplicate remove: {before_count} → {after_count} (removed {before_count - after_count})')
    return entries


def save_outputs(online_movies, offline_movies, online_tv, offline_tv):
    write_json(MOVIE_JSON, online_movies)
    write_json(OFFLINE_MOVIE_JSON, offline_movies)
    write_m3u(OFFLINE_MOVIE_M3U, offline_movies)
    write_json(LIVE_TV_JSON, online_tv)
    write_m3u(LIVE_TV_M3U, online_tv)
    write_json(OFFLINE_TV_JSON, offline_tv)
    write_m3u(OFFLINE_TV_M3U, offline_tv)


def main():
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    entries = load_all_entries()

    all_movies = [e for e in entries if classify_entry(e) == 'movie']
    all_tv = [e for e in entries if classify_entry(e) == 'tv']

    print(f'\nChecking {len(all_movies)} movie URLs...')
    online_movies, offline_movies = split_online_offline(all_movies)

    print(f'\nChecking {len(all_tv)} TV URLs...')
    online_tv, offline_tv = split_online_offline(all_tv)

    save_outputs(online_movies, offline_movies, online_tv, offline_tv)

    counter = Counter(e.get('group', 'Other') for e in entries)
    with open(REPORT, 'w', encoding='utf-8') as handle:
        handle.write('Processor Report\n================\n')
        handle.write(f'Total entries   : {len(entries)}\n')
        handle.write(f'Movies (online) : {len(online_movies)}\n')
        handle.write(f'Movies (offline): {len(offline_movies)}\n')
        handle.write(f'TV (online)     : {len(online_tv)}\n')
        handle.write(f'TV (offline)    : {len(offline_tv)}\n')
        handle.write('Top groups:\n')
        for group, count in counter.most_common(20):
            handle.write(f'  - {group}: {count}\n')

    print('\nPROCESS COMPLETED')
    print(f'Movies online : {len(online_movies)}, offline: {len(offline_movies)}')
    print(f'TV online     : {len(online_tv)}, offline: {len(offline_tv)}')


if __name__ == '__main__':
    main()
