
from core.duplicate_remover import remove_duplicates
from core.validator import is_alive

streams = [
    {"name": "Demo TV", "url": "https://example.com/live.m3u8"}
]

streams = remove_duplicates(streams)

alive = [s for s in streams if is_alive(s["url"])]

print("Working Streams:", len(alive))
