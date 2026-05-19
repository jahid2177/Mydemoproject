"""
EPG Support — gzip compressed XML support সহ
"""
import gzip
import io
import xml.etree.ElementTree as ET
from typing import Dict, Iterable

import requests

from core.playlist_utils import normalize_name

HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) EPGSupport/1.0',
           'Accept-Encoding': 'gzip, deflate'}


def _fetch_epg_content(url: str, timeout: int) -> bytes:
    """URL থেকে EPG content নিয়ে আসে — gzip এবং plain XML দুটোই handle করে"""
    resp = requests.get(url, timeout=timeout, headers=HEADERS, stream=True)
    resp.raise_for_status()
    raw = resp.content

    # ✅ FIX: gzip magic bytes চেক করে decompress করি
    if raw[:2] == b'\x1f\x8b':
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as gz:
            return gz.read()
    return raw


def load_epg(epg_urls: Iterable[str], timeout: int = 20) -> Dict[str, dict]:
    epg_map = {}
    for url in [u for u in dict.fromkeys(epg_urls or []) if u]:
        try:
            content = _fetch_epg_content(url, timeout)
            root = ET.fromstring(content)

            for channel in root.findall('channel'):
                channel_id = (channel.get('id') or '').strip()
                display_names = [
                    node.text.strip()
                    for node in channel.findall('display-name')
                    if node.text
                ]
                icon = channel.find('icon')
                payload = {
                    'epg_id':   channel_id,
                    'epg_name': display_names[0] if display_names else '',
                    'logo':     icon.get('src', '') if icon is not None else '',
                }
                if channel_id:
                    epg_map[channel_id] = payload
                for name in display_names:
                    epg_map[normalize_name(name)] = payload

            print(f'EPG loaded: {len(epg_map)} channels from {url}')
        except Exception as exc:
            print(f'EPG load failed ({url}): {exc}')
            continue

    return epg_map


def apply_epg(streams, epg_map):
    if not epg_map:
        return streams
    matched = 0
    for stream in streams:
        keys = [
            stream.get('epg_id', ''),
            normalize_name(stream.get('epg_name') or stream.get('name', '')),
        ]
        match = None
        for key in keys:
            if key and key in epg_map:
                match = epg_map[key]
                break
        if match:
            matched += 1
            stream['epg_id']   = stream.get('epg_id')   or match.get('epg_id', '')
            stream['epg_name'] = stream.get('epg_name') or match.get('epg_name', '')
            if not stream.get('logo') and match.get('logo'):
                stream['logo'] = match['logo']

    print(f'EPG applied: {matched}/{len(streams)} streams matched')
    return streams
