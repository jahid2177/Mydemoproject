"""
Stream Cleaner — সবসময় (working, offline) tuple return করে
"""


def clean_dead(streams, checks=None):
    """
    streams: list of stream dicts
    checks:  list of check result dicts (url, alive, error, ...)
             None হলে streams এর নিজের 'alive' field দেখে

    Returns: (working_list, offline_list)  ← সবসময় tuple
    """
    # ✅ FIX: checks=None case এও tuple return করে এখন
    if checks is None:
        working  = [s for s in streams if s.get('alive', True)]
        offline  = [s for s in streams if not s.get('alive', True)]
        return working, offline

    status_map = {item['url']: item for item in checks}
    working, offline = [], []

    for stream in streams:
        status = status_map.get(stream.get('url', ''))
        if status is None:
            # unchecked stream — alive ধরে নিই
            stream.setdefault('alive', True)
            working.append(stream)
        elif status.get('alive'):
            stream['alive'] = True
            stream.pop('last_error', None)
            working.append(stream)
        else:
            stream['alive'] = False
            stream['last_error'] = status.get('error', '')
            offline.append(stream)

    return working, offline
