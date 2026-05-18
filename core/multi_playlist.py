
def merge_playlists(files):
    merged = []

    for file in files:
        with open(file, "r", encoding="utf-8") as f:
            merged.extend(f.readlines())

    return merged
