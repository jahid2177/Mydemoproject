"""
Multi Playlist — EPG URLs সহ return করে
"""
from core.duplicate_remover import remove_duplicates
from core.playlist_utils import load_playlist_file


def merge_playlists(files, dedupe=True):
    """
    একাধিক M3U file merge করে।
    Returns: merged stream list (EPG urls এখন discover_local থেকে separately নেওয়া হয়)
    """
    merged = []
    epg_urls = []

    for file in files:
        try:
            entries, found_epg = load_playlist_file(file)
            merged.extend(entries)
            epg_urls.extend(found_epg)
        except Exception as exc:
            print(f'Warning: could not load {file}: {exc}')

    if dedupe:
        merged = remove_duplicates(merged)

    # ✅ FIX: epg_urls ও return করা হচ্ছে — caller চাইলে use করতে পারবে
    return merged, list(dict.fromkeys(epg_urls))
