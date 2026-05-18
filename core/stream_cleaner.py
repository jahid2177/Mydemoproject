def clean_dead(streams, checks=None):
    if checks is None:
        return [stream for stream in streams if stream.get('alive', True)]

    status_map = {item['url']: item for item in checks}
    working = []
    offline = []
    for stream in streams:
        status = status_map.get(stream.get('url'))
        if status and status.get('alive'):
            stream['alive'] = True
            working.append(stream)
        elif status:
            stream['alive'] = False
            stream['last_error'] = status.get('error', '')
            offline.append(stream)
        else:
            working.append(stream)
    return working, offline
