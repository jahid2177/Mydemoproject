"""
Xtream Codes Parser — সঠিক API endpoint ও response key সহ
"""
from urllib.parse import urlencode

import requests

HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) XtreamParser/1.0'}


def _api_call(server, username, password, action, timeout=15):
    url = f"{server}/player_api.php?{urlencode({'username': username, 'password': password, 'action': action})}"
    resp = requests.get(url, timeout=timeout, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def parse_xtream(server, username, password, stream_type='live', timeout=15):
    """
    Xtream Codes API থেকে stream list নিয়ে আসে।

    stream_type:
      'live'  → get_live_streams
      'vod'   → get_vod_streams
      'series'→ get_series
    """
    server = server.rstrip('/')

    # ✅ FIX: সঠিক action parameter ও response key
    action_map = {
        'live':   'get_live_streams',
        'vod':    'get_vod_streams',
        'series': 'get_series',
    }
    action = action_map.get(stream_type, 'get_live_streams')

    try:
        items = _api_call(server, username, password, action, timeout)
    except Exception as exc:
        print(f'Xtream API error ({action}): {exc}')
        return []

    if not isinstance(items, list):
        print(f'Xtream: unexpected response type {type(items)} for action={action}')
        return []

    entries = []
    for item in items:
        stream_id = item.get('stream_id') or item.get('series_id')
        if not stream_id:
            continue

        if stream_type == 'live':
            url = f'{server}/live/{username}/{password}/{stream_id}.m3u8'
        elif stream_type == 'vod':
            ext = item.get('container_extension', 'mp4')
            url = f'{server}/movie/{username}/{password}/{stream_id}.{ext}'
        else:
            # series — episode level url আলাদা, category URL দিই
            url = f'{server}/series/{username}/{password}/{stream_id}.m3u8'

        # category নাম সংগ্রহ করি (live → category_name, vod → category_name)
        group = (
            item.get('category_name')
            or item.get('category_id', '')
            or ('Live TV' if stream_type == 'live' else 'VOD')
        )

        entries.append({
            'name':     item.get('name', 'Unknown'),
            'logo':     item.get('stream_icon') or item.get('cover', ''),
            'group':    str(group),
            'url':      url,
            'source':   server,
            'epg_id':   item.get('epg_channel_id', ''),
            'epg_name': item.get('name', ''),
        })

    return entries
