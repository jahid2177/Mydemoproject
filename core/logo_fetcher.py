"""
Auto Logo Fetcher
- ui-avatars.com API fail করলে default logo ব্যবহার করে
- existing logo overwrite করে না
"""
import os
from urllib.parse import quote_plus

import requests

DEFAULT_LOGO = (
    'https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/logo/default-logo.png'
)
AVATAR_API = 'https://ui-avatars.com/api/?name={name}&background=0D8ABC&color=fff&size=256&bold=true'


def _build_avatar_url(channel_name: str) -> str:
    name = (channel_name or 'IPTV').strip()[:50]
    return AVATAR_API.format(name=quote_plus(name))


def _is_valid_logo_url(url: str) -> bool:
    """Logo URL টি reachable কিনা চেক করে — timeout 5s"""
    if not url or not url.startswith('http'):
        return False
    try:
        r = requests.head(url, timeout=5, allow_redirects=True,
                          headers={'User-Agent': 'Mozilla/5.0'})
        return r.status_code < 400
    except Exception:
        return False


def fetch_logo(channel_name: str) -> str:
    """
    channel_name থেকে logo URL তৈরি করে।
    ui-avatars.com fail করলে DEFAULT_LOGO return করে।
    """
    avatar_url = _build_avatar_url(channel_name)
    if _is_valid_logo_url(avatar_url):
        return avatar_url
    return DEFAULT_LOGO


def apply_logos(streams, default_logo: str = DEFAULT_LOGO):
    """
    Streams এ logo assign করে।
    ✅ FIX: বিদ্যমান valid logo overwrite করে না।
    ✅ FIX: API fail হলে default_logo দেয়।
    """
    for stream in streams:
        existing = (stream.get('logo') or '').strip()
        if existing and existing.startswith('http'):
            # ইতিমধ্যে logo আছে — পরিবর্তন না করি
            continue
        name = stream.get('name', 'IPTV')
        # ui-avatars এ network issue হলে default logo
        try:
            stream['logo'] = fetch_logo(name)
        except Exception:
            stream['logo'] = default_logo
    return streams
