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
OFFLINE_MOVIE_JSON = os.path.join(BASE_DIR, 'ofline movie.json')
OFFLINE_MOVIE_M3U = os.path.join(BASE_DIR, 'ofline movie.m3u')
LIVE_TV_JSON = os.path.join(LIVE_TV_DIR, 'live_tv.json')
LIVE_TV_M3U = os.path.join(LIVE_TV_DIR, 'live_tv.m3u')
OFFLINE_TV_JSON = os.path.join(LIVE_TV_DIR, 'ofline Tv.json')
OFFLINE_TV_M3U = os.path.join(LIVE_TV_DIR, 'ofline Tv.m3u')
REPORT = os.path.join(BASE_DIR, 'logs', 'processor_report.txt')

REMOTE_URLS = [
    'https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/Bollywood/Movies.m3u',
    'https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/Bengali/Movies.m3u',
    'https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/Hollywood/Movies.m3u',
    'https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/WorldwideVOD/Movies.m3u',
    'https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/SouthIndian/Movies.m3u',
]


def load_remote_playlist(url):
    try:
        response = requests.get(url, timeout=25, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            return parse_m3u_text(response.text, source=url)[0]
        print(f'Skip remote {url} -> HTTP {response.status_code}')
    except Exception as exc:
        print(f'Skip remote {url} -> {exc}')
    return []


def load_all_entries():
    local_files = [path for path in discover_local_playlists(BASE_DIR) if os.path.basename(path) == 'Movies.m3u']
    entries = []
    if local_files:
        for path in local_files:
            with open(path, 'r', encoding='utf-8', errors='ignore') as handle:
                entries.extend(parse_m3u_text(handle.read(), source=path)[0])
    else:
        for url in REMOTE_URLS:
            entries.extend(load_remote_playlist(url))
    return remove_duplicates(apply_logos(entries))


def save_outputs(movies, tv):
    write_json(MOVIE_JSON, movies)
    write_json(OFFLINE_MOVIE_JSON, [])
    write_json(LIVE_TV_JSON, tv)
    write_json(OFFLINE_TV_JSON, [])
    write_m3u(OFFLINE_MOVIE_M3U, [])
    write_m3u(LIVE_TV_M3U, tv)
    write_m3u(OFFLINE_TV_M3U, [])


def main():
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    entries = load_all_entries()
    movies = [entry for entry in entries if classify_entry(entry) == 'movie']
    tv = [entry for entry in entries if classify_entry(entry) == 'tv']
    save_outputs(movies, tv)

    counter = Counter(entry.get('group', 'Other') for entry in entries)
    with open(REPORT, 'w', encoding='utf-8') as handle:
        handle.write('Processor Report\n')
        handle.write('================\n')
        handle.write(f'Total entries: {len(entries)}\n')
        handle.write(f'Movies: {len(movies)}\n')
        handle.write(f'TV: {len(tv)}\n')
        handle.write('Top groups:\n')
        for group, count in counter.most_common(20):
            handle.write(f'- {group}: {count}\n')

    print('PROCESS COMPLETED')
    print('Total Movies :', len(movies))
    print('Total TV     :', len(tv))
    print('all_movies.json ->', MOVIE_JSON)


if __name__ == '__main__':
    main()
