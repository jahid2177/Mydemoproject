from core.duplicate_remover import remove_duplicates
from core.playlist_utils import load_playlist_file


def merge_playlists(files, dedupe=True):
    merged = []
    epg_urls = []
    for file in files:
        entries, found_epg = load_playlist_file(file)
        merged.extend(entries)
        epg_urls.extend(found_epg)
    if dedupe:
        merged = remove_duplicates(merged)
    return merged
