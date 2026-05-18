
def remove_duplicates(streams):
    seen = set()
    result = []

    for stream in streams:
        if stream["url"] not in seen:
            seen.add(stream["url"])
            result.append(stream)

    return result
