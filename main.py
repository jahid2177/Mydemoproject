import asyncio
import glob
import json
import os
from datetime import datetime, timezone

from api.json_export import export_json
from core.async_checker import check_streams
from core.category_sorter import sort_category
from core.duplicate_remover import remove_duplicates
from core.epg_support import apply_epg, load_epg
from core.hls_validator import validate_hls
from core.logo_fetcher import apply_logos
from core.multi_playlist import merge_playlists
from core.playlist_utils import classify_entry, discover_local_playlists, ensure_dir, write_m3u
from core.poster_generator import fetch_poster
from core.quality_detector import detect_quality
from core.stream_cleaner import clean_dead
from core.xtream_parser import parse_xtream

BASE_DIR = os.getcwd()
OUTPUT_DIR = os.path.join(BASE_DIR, 'data', 'output')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
POSTER_DIR = os.path.join(BASE_DIR, 'assets', 'posters')
REPORT_FILE = os.path.join(LOG_DIR, 'test_report.txt')

CHECK_LIMIT = int(os.getenv('CHECK_LIMIT', '120'))
QUALITY_LIMIT = int(os.getenv('QUALITY_LIMIT', '30'))
POSTER_LIMIT = int(os.getenv('POSTER_LIMIT', '6'))


def load_streams():
    playlist_files = discover_local_playlists(BASE_DIR)
    extra = [item.strip() for item in os.getenv('EXTRA_PLAYLISTS', '').split(',') if item.strip()]
    playlist_files.extend(extra)
    playlist_files = sorted(dict.fromkeys(playlist_files))
    streams = merge_playlists(playlist_files) if playlist_files else []

    xtream_entries = []
    xtream_codes = [item.strip() for item in os.getenv('XTREAM_CODES', '').split(';') if item.strip()]
    for code in xtream_codes:
        parts = [part.strip() for part in code.split('|')]
        if len(parts) == 3:
            try:
                xtream_entries.extend(parse_xtream(parts[0], parts[1], parts[2]))
            except Exception:
                pass

    return playlist_files, streams + xtream_entries


def main():
    ensure_dir(OUTPUT_DIR)
    ensure_dir(LOG_DIR)
    ensure_dir(POSTER_DIR)

    playlist_files, streams = load_streams()
    streams = remove_duplicates(streams)
    streams = apply_logos(streams)

    epg_urls = [item.strip() for item in os.getenv('EPG_URLS', '').split(',') if item.strip()]
    epg_map = load_epg(epg_urls)
    streams = apply_epg(streams, epg_map)

    sample_to_check = streams[:CHECK_LIMIT]
    checked = asyncio.run(check_streams(sample_to_check, concurrency=40, timeout=8)) if sample_to_check else []
    checked_alive, checked_dead = clean_dead(sample_to_check, checked) if sample_to_check else ([], [])
    survivors = checked_alive + streams[CHECK_LIMIT:]

    quality_targets = [stream for stream in survivors if '.m3u8' in stream.get('url', '').lower()][:QUALITY_LIMIT]
    for stream in quality_targets:
        stream['quality'] = detect_quality(stream)
        stream['hls_valid'] = validate_hls(stream.get('url'))

    grouped = sort_category(survivors)
    movies = [stream for stream in survivors if classify_entry(stream) == 'movie']
    tv = [stream for stream in survivors if classify_entry(stream) == 'tv']

    poster_files = [fetch_poster(stream, output_dir=POSTER_DIR) for stream in movies[:POSTER_LIMIT]]

    payload = {
        'generated_at_utc': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'playlist_files': playlist_files,
        'feature_summary': {
            'async_stream_checker': bool(checked),
            'auto_logo_fetcher': True,
            'multi_playlist_support': True,
            'json_api_export': True,
            'xtream_parser': True,
            'duplicate_link_remove': True,
            'broken_stream_auto_delete': True,
            'stream_quality_detect': True,
            'poster_generator': True,
            'epg_support': bool(epg_urls),
            'hls_validation': True,
            'iptv_category_sort': True,
        },
        'counts': {
            'total_streams': len(streams),
            'after_cleanup': len(survivors),
            'checked_streams': len(sample_to_check),
            'dead_removed_from_checked_set': len(checked_dead),
            'movies': len(movies),
            'tv': len(tv),
        },
        'groups': grouped,
    }

    export_json(payload, os.path.join(OUTPUT_DIR, 'streams.json'))
    export_json(movies, os.path.join(OUTPUT_DIR, 'movies.json'))
    export_json(tv, os.path.join(OUTPUT_DIR, 'live_tv.json'))
    write_m3u(os.path.join(OUTPUT_DIR, 'playlist.m3u'), survivors, epg_urls=epg_urls)

    with open(REPORT_FILE, 'w', encoding='utf-8') as handle:
        handle.write('IPTV Feature Check Report\n')
        handle.write('=========================\n')
        handle.write(f'Loaded playlist files: {len(playlist_files)}\n')
        handle.write(f'Total parsed streams: {len(streams)}\n')
        handle.write(f'Checked streams: {len(sample_to_check)}\n')
        handle.write(f'Dead removed (checked set): {len(checked_dead)}\n')
        handle.write(f'Final streams: {len(survivors)}\n')
        handle.write(f'Movie entries: {len(movies)}\n')
        handle.write(f'TV entries: {len(tv)}\n')
        handle.write(f'Poster files: {len(poster_files)}\n')
        handle.write(f'EPG loaded: {len(epg_map)}\n')
        handle.write('\nSample quality checks:\n')
        for stream in quality_targets[:10]:
            handle.write(f'- {stream.get("name")} => {stream.get("quality", "Unknown")} | HLS: {stream.get("hls_valid", False)}\n')

    print('Loaded playlists:', len(playlist_files))
    print('Total streams:', len(streams))
    print('Final streams:', len(survivors))
    print('Output JSON:', os.path.join(OUTPUT_DIR, 'streams.json'))
    print('Report:', REPORT_FILE)


if __name__ == '__main__':
    main()
