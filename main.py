"""
IPTV Ultimate System — সব feature সঠিকভাবে কাজ করছে
Features:
  ✅ Async Stream Checker
  ✅ Auto Logo Fetcher        (FIX: existing logo overwrite করে না, API fail হলে default)
  ✅ Multi-playlist Support
  ✅ JSON API Export
  ✅ Xtream Parser            (FIX: XTREAM_CODES না থাকলে clearly log করে)
  ✅ Duplicate Link Remove
  ✅ Auto GitHub Commit       (FIX: workflow এ concurrency + retry)
  ✅ Broken Stream Auto Delete
  ✅ Stream Quality Detect    (FIX: ffprobe optional, graceful fallback)
  ✅ Poster Generator
  ✅ EPG Support (gzip সহ)
  ✅ HLS Validation           (FIX: Content-Type ও redirect handle করে)
  ✅ IPTV Category Sort
"""
import asyncio
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

BASE_DIR    = os.getcwd()
OUTPUT_DIR  = os.path.join(BASE_DIR, 'data', 'output')
LOG_DIR     = os.path.join(BASE_DIR, 'logs')
POSTER_DIR  = os.path.join(BASE_DIR, 'assets', 'posters')
REPORT_FILE = os.path.join(LOG_DIR, 'test_report.txt')

CHECK_LIMIT   = int(os.getenv('CHECK_LIMIT',   '200'))
QUALITY_LIMIT = int(os.getenv('QUALITY_LIMIT', '30'))
POSTER_LIMIT  = int(os.getenv('POSTER_LIMIT',  '10'))


def load_streams():
    playlist_files = discover_local_playlists(BASE_DIR)
    extra = [i.strip() for i in os.getenv('EXTRA_PLAYLISTS', '').split(',') if i.strip()]
    playlist_files.extend(extra)
    playlist_files = sorted(dict.fromkeys(playlist_files))

    if playlist_files:
        streams, m3u_epg_urls = merge_playlists(playlist_files)
        print(f'[Playlist] {len(playlist_files)} file(s) loaded → {len(streams)} entries')
    else:
        streams, m3u_epg_urls = [], []
        print('[Playlist] কোনো local playlist file পাওয়া যায়নি')

    # Xtream Codes support
    xtream_entries = []
    xtream_codes_env = os.getenv('XTREAM_CODES', '').strip()
    if xtream_codes_env:
        for code in xtream_codes_env.split(';'):
            parts = [p.strip() for p in code.split('|')]
            if len(parts) >= 3:
                try:
                    xtream_entries.extend(parse_xtream(parts[0], parts[1], parts[2], stream_type='live'))
                    xtream_entries.extend(parse_xtream(parts[0], parts[1], parts[2], stream_type='vod'))
                except Exception as exc:
                    print(f'[Xtream] Parse error: {exc}')
        print(f'[Xtream] {len(xtream_entries)} entries loaded')
    else:
        # ✅ FIX: clearly log করা হচ্ছে — silently skip না করে
        print('[Xtream] XTREAM_CODES env variable set নেই — Xtream parser skip হচ্ছে')

    all_streams = streams + xtream_entries

    env_epg = [i.strip() for i in os.getenv('EPG_URLS', '').split(',') if i.strip()]
    combined_epg = list(dict.fromkeys(m3u_epg_urls + env_epg))

    return playlist_files, all_streams, combined_epg


def main():
    ensure_dir(OUTPUT_DIR)
    ensure_dir(LOG_DIR)
    ensure_dir(POSTER_DIR)

    # ── 1. Load & Deduplicate ──────────────────────────────────────────────
    playlist_files, streams, epg_urls = load_streams()
    before_dedup = len(streams)
    streams = remove_duplicates(streams)
    print(f'[Duplicate Remove] {before_dedup} → {len(streams)} (removed {before_dedup - len(streams)})')

    if not streams:
        print('[WARNING] কোনো stream নেই — empty output তৈরি হবে')

    # ── 2. Auto Logo Fetcher ───────────────────────────────────────────────
    # ✅ FIX: existing logo preserve করে, API fail হলে default logo দেয়
    streams = apply_logos(streams)
    print(f'[Logo Fetcher] Applied logos to {len(streams)} streams')

    # ── 3. EPG Support (gzip সহ) ──────────────────────────────────────────
    epg_map = load_epg(epg_urls)
    streams = apply_epg(streams, epg_map)

    # ── 4. Async Stream Checker + Broken Stream Auto Delete ───────────────
    sample_to_check = streams[:CHECK_LIMIT]
    unchecked = streams[CHECK_LIMIT:]

    if sample_to_check:
        print(f'[Async Checker] Checking {len(sample_to_check)} streams...')
        checked_results = asyncio.run(check_streams(sample_to_check, concurrency=50, timeout=8))
        checked_alive, checked_dead = clean_dead(sample_to_check, checked_results)
        print(f'[Broken Stream Delete] alive={len(checked_alive)}, dead={len(checked_dead)}')
    else:
        checked_alive, checked_dead = [], []

    survivors = checked_alive + unchecked
    print(f'[Survivors] {len(survivors)} streams remaining')

    # ── 5. Stream Quality Detect + HLS Validation ─────────────────────────
    # ✅ FIX: ffprobe না থাকলেও quality_detector HLS playlist থেকে detect করে
    quality_targets = [
        s for s in survivors if '.m3u8' in s.get('url', '').lower()
    ][:QUALITY_LIMIT]

    for stream in quality_targets:
        stream['quality']   = detect_quality(stream)
        stream['hls_valid'] = validate_hls(stream.get('url'))

    print(f'[Quality Detect] Checked {len(quality_targets)} HLS streams')

    # ── 6. IPTV Category Sort ──────────────────────────────────────────────
    grouped = sort_category(survivors)
    print(f'[Category Sort] {len(grouped)} categories')

    # ── 7. Classify movies vs TV ──────────────────────────────────────────
    movies = [s for s in survivors if classify_entry(s) == 'movie']
    tv     = [s for s in survivors if classify_entry(s) == 'tv']
    print(f'[Classify] Movies: {len(movies)}, TV: {len(tv)}')

    # ── 8. Poster Generator ───────────────────────────────────────────────
    poster_files = [fetch_poster(s, output_dir=POSTER_DIR) for s in movies[:POSTER_LIMIT]]
    print(f'[Poster Generator] Generated {len(poster_files)} posters')

    # ── 9. JSON API Export ────────────────────────────────────────────────
    payload = {
        'generated_at_utc': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'playlist_files': playlist_files,
        'feature_summary': {
            'async_stream_checker':      bool(sample_to_check),
            'auto_logo_fetcher':         True,
            'multi_playlist_support':    len(playlist_files) > 0,
            'json_api_export':           True,
            'xtream_parser':             bool(os.getenv('XTREAM_CODES', '')),
            'duplicate_link_remove':     True,
            'broken_stream_auto_delete': True,
            'stream_quality_detect':     len(quality_targets) > 0,
            'poster_generator':          len(poster_files) > 0,
            'epg_support':               len(epg_map) > 0,
            'hls_validation':            True,
            'iptv_category_sort':        len(grouped) > 0,
        },
        'counts': {
            'total_streams':           before_dedup,
            'after_dedup':             len(streams),
            'checked_streams':         len(sample_to_check),
            'dead_removed':            len(checked_dead),
            'alive_after_check':       len(checked_alive),
            'final_survivors':         len(survivors),
            'movies':                  len(movies),
            'tv':                      len(tv),
            'epg_channels_loaded':     len(epg_map),
            'quality_checked_streams': len(quality_targets),
            'posters_generated':       len(poster_files),
            'category_groups':         len(grouped),
        },
        'groups': grouped,
    }

    export_json(payload, os.path.join(OUTPUT_DIR, 'streams.json'))
    export_json(movies,  os.path.join(OUTPUT_DIR, 'movies.json'))
    export_json(tv,      os.path.join(OUTPUT_DIR, 'live_tv.json'))
    write_m3u(os.path.join(OUTPUT_DIR, 'playlist.m3u'), survivors, epg_urls=epg_urls)

    # ── 10. Report ────────────────────────────────────────────────────────
    with open(REPORT_FILE, 'w', encoding='utf-8') as fh:
        fh.write('IPTV Feature Check Report\n')
        fh.write('=========================\n')
        fh.write(f'Playlist files loaded : {len(playlist_files)}\n')
        fh.write(f'Total parsed streams  : {before_dedup}\n')
        fh.write(f'After duplicate remove: {len(streams)}\n')
        fh.write(f'Checked (async)       : {len(sample_to_check)}\n')
        fh.write(f'Dead removed          : {len(checked_dead)}\n')
        fh.write(f'Final survivors       : {len(survivors)}\n')
        fh.write(f'Movies                : {len(movies)}\n')
        fh.write(f'TV channels           : {len(tv)}\n')
        fh.write(f'Posters generated     : {len(poster_files)}\n')
        fh.write(f'EPG channels loaded   : {len(epg_map)}\n')
        fh.write(f'Category groups       : {len(grouped)}\n')
        fh.write('\nSample quality checks:\n')
        for s in quality_targets[:15]:
            fh.write(
                f'  - {s.get("name", "?")} => {s.get("quality", "Unknown")} '
                f'| HLS valid: {s.get("hls_valid", False)}\n'
            )

    print('\n===== PROCESS COMPLETED =====')
    print(f'Total: {before_dedup} → dedup: {len(streams)} → survivors: {len(survivors)}')
    print(f'Movies: {len(movies)}, TV: {len(tv)}, Dead removed: {len(checked_dead)}')
    print(f'Output: {OUTPUT_DIR}')


if __name__ == '__main__':
    main()
