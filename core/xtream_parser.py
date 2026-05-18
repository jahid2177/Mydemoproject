from urllib.parse import urlencode

import requests


def parse_xtream(server, username, password, stream_type='live', timeout=15):
    server = server.rstrip('/')
    api_url = f'{server}/player_api.php?{urlencode({"username": username, "password": password})}'
    response = requests.get(api_url, timeout=timeout)
    response.raise_for_status()
    data = response.json()

    entries = []
    if stream_type == 'live':
        for item in data.get('available_channels', []):
            stream_id = item.get('stream_id')
            if not stream_id:
                continue
            entries.append({
                'name': item.get('name', 'Unknown'),
                'logo': item.get('stream_icon', ''),
                'group': item.get('category_name', 'Xtream Live'),
                'url': f'{server}/live/{username}/{password}/{stream_id}.m3u8',
                'source': api_url,
                'epg_id': item.get('epg_channel_id', ''),
                'epg_name': item.get('name', ''),
            })
    return entries
