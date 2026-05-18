def remove_duplicates(streams):
    seen = set()
    result = []
    for stream in streams:
        url = (stream.get('url') if isinstance(stream, dict) else str(stream)).strip()
        key = url.lower()
        if key and key not in seen:
            seen.add(key)
            result.append(stream)
    return result
