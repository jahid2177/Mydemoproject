
from core.async_checker import check_streams
from core.multi_playlist import merge_playlists

playlists = [
    "data/input/sample1.m3u",
    "data/input/sample2.m3u"
]

merged = merge_playlists(playlists)

print("Merged Streams:", len(merged))
