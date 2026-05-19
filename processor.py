import asyncio
import os
from collections import Counter

import aiohttp
import requests

from core.duplicate_remover import remove_duplicates
from core.logo_fetcher import apply_logos
from core.playlist_utils import classify_entry, discover_local_playlists, parse_m3u_text, write_json, write_m3u

BASE_DIR = os.getcwd()
LIVE_TV_DIR = os.path.join(BASE_DIR, 'LiveTV')
os.makedirs(LIVE_TV_DIR, exist_ok=True)

# ─── Output file paths (underscore — URL-এ space কাজ করে না) ─────────────────
MOVIE_JSON         = os.path.join(BASE_DIR,    'all_movies.json')
OFFLINE_MOVIE_JSON = os.path.join(BASE_DIR,    'offline_movie.json')
OFFLINE_MOVIE_M3U  = os.path.join(BASE_DIR,    'offline_movie.m3u')
LIVE_TV_JSON       = os.path.join(LIVE_TV_DIR, 'live_tv.json')
LIVE_TV_M3U        = os.path.join(LIVE_TV_DIR, 'live_tv.m3u')
OFFLINE_TV_JSON    = os.path.join(LIVE_TV_DIR, 'offline_tv.json')
OFFLINE_TV_M3U     = os.path.join(LIVE_TV_DIR, 'offline_tv.m3u')
REPORT             = os.path.join(BASE_DIR,    'logs', 'processor_report.txt')

# ─── পুরনো space-নামের files মুছে দাও ──────────────────────────────────────
_OLD_FILES = [
    os.path.join(BASE_DIR,    'offline movie.json'),
    os.path.join(BASE_DIR,    'offline movie.m3u'),
    os.path.join(LIVE_TV_DIR, 'offline Tv.json'),
    os.path.join(LIVE_TV_DIR, 'offline Tv.m3u'),
]
for _f in _OLD_FILES:
    if os.path.exists(_f):
        os.remove(_f)
        print(f'Deleted old file: {_f}')

REMOTE_URLS = [
    'https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/Bollywood/Movies.m3u',
    'https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/Bengali/Movies.m3u',
    'https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/Hollywood/Movies.m3u',
    'https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/WorldwideVOD/Movies.m3u',
    'https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/SouthIndian/Movies.m3u',
]

CHECK_TIMEOUT     = int(os.getenv('CHECK_TIMEOUT', '8'))
CHECK_CONCURRENCY = int(os.getenv('CHECK_CONCURRENCY', '80'))
USER_AGENT = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) IPTVProcessor/2.0'}


def load_remote_playlist(url):
    try:
        response = requests.get(url, timeout=25, headers=USER_AGENT)
        if response.status_code == 200:
            return parse_m3u_text(response.text, source=url)[0]
        print(f'Skip remote {url} -> HTTP {response.status_code}')
    except Exception as exc:
        print(f'Skip remote {url} -> {exc}')
    return []


async def _check_one(session, entry, semaphore):
    url = entry.get('url', '')
    if not url:
        return {**entry, '_online': False}
    async with semaphore:
        for method in ('HEAD', 'GET'):
            try:
                fn = session.head if method == 'HEAD' else session.get
                async with fn(
                    url, allow_redirects=True,
                    timeout=aiohttp.ClientTimeout(total=CHECK_TIMEOUT),
                    headers=USER_AGENT,
                ) as resp:
                    if resp.status < 400:
                        return {**entry, '_online': True}
            except Exception:
                pass
    return {**entry, '_online': False}


async def _check_all_async(entries):
    semaphore = asyncio.Semaphore(CHECK_CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=CHECK_CONCURRENCY, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        return await asyncio.gather(*[_check_one(session, e, semaphore) for e in entries])


def split_online_offline(entries):
    if not entries:
        return [], []
    results = asyncio.run(_check_all_async(entries))
    online, offline = [], []
    for r in results:
        flag = r.pop('_online', False)
        (online if flag else offline).append(r)
    print(f'  online: {len(online)}, offline: {len(offline)}')
    return online, offline


def load_all_entries():
    local_files = [
        p for p in discover_local_playlists(BASE_DIR)
        if os.path.basename(p) == 'Movies.m3u'
    ]
    raw = []
    if local_files:
        for path in local_files:
            with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                raw.extend(parse_m3u_text(fh.read(), source=path)[0])
    else:
        for url in REMOTE_URLS:
            raw.extend(load_remote_playlist(url))

    before = len(raw)
    entries = remove_duplicates(apply_logos(raw))
    print(f'Duplicate remove: {before} -> {len(entries)} (removed {before - len(entries)})')
    return entries


def save_outputs(online_movies, offline_movies, online_tv, offline_tv):
    write_json(MOVIE_JSON,         online_movies)
    write_json(OFFLINE_MOVIE_JSON, offline_movies)
    write_m3u( OFFLINE_MOVIE_M3U,  offline_movies)
    write_json(LIVE_TV_JSON,       online_tv)
    write_m3u( LIVE_TV_M3U,        online_tv)
    write_json(OFFLINE_TV_JSON,    offline_tv)
    write_m3u( OFFLINE_TV_M3U,     offline_tv)


def main():
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    entries = load_all_entries()

    all_movies = [e for e in entries if classify_entry(e) == 'movie']
    all_tv     = [e for e in entries if classify_entry(e) == 'tv']
    print(f'Classified -> Movies: {len(all_movies)}, TV: {len(all_tv)}')

    print(f'\nChecking {len(all_movies)} movie URLs (async)...')
    online_movies, offline_movies = split_online_offline(all_movies)

    print(f'\nChecking {len(all_tv)} TV URLs (async)...')
    online_tv, offline_tv = split_online_offline(all_tv)

    save_outputs(online_movies, offline_movies, online_tv, offline_tv)

    counter = Counter(e.get('group', 'Other') for e in entries)
    with open(REPORT, 'w', encoding='utf-8') as fh:
        fh.write('Processor Report\n================\n')
        fh.write(f'Total entries    : {len(entries)}\n')
        fh.write(f'Movies (online)  : {len(online_movies)}\n')
        fh.write(f'Movies (offline) : {len(offline_movies)}\n')
        fh.write(f'TV (online)      : {len(online_tv)}\n')
        fh.write(f'TV (offline)     : {len(offline_tv)}\n')
        fh.write('Top groups:\n')
        for group, count in counter.most_common(20):
            fh.write(f'  - {group}: {count}\n')

    print('\nPROCESS COMPLETED')
    print(f'Movies  -> online: {len(online_movies)}, offline: {len(offline_movies)}')
    print(f'TV      -> online: {len(online_tv)}, offline: {len(offline_tv)}')


if __name__ == '__main__':
    main()
