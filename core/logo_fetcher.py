"""
Auto Logo Fetcher
✅ FIX: প্রতি stream এ HTTP call বাদ — GitHub Actions এ হাজার stream হলে timeout হত
✅ FIX: existing valid logo overwrite করে না
✅ FIX: ui-avatars.com URL তৈরি করে, reachable কিনা check করে না (fast)
"""
from urllib.parse import quote_plus

DEFAULT_LOGO = (
    'https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/logo/default-logo.png'
)
AVATAR_BASE = (
    'https://ui-avatars.com/api/'
    '?background=0D8ABC&color=fff&size=256&bold=true&name='
)


def _build_avatar_url(channel_name: str) -> str:
    """Channel name থেকে avatar URL তৈরি করে — কোনো HTTP call নেই।"""
    name = (channel_name or 'IPTV').strip()[:50]
    return AVATAR_BASE + quote_plus(name)


def apply_logos(streams, default_logo: str = DEFAULT_LOGO):
    """
    Streams এ logo assign করে।
    ✅ বিদ্যমান http logo থাকলে পরিবর্তন করে না।
    ✅ প্রতি stream এ HTTP call নেই — তাই দ্রুত।
    ✅ logo না থাকলে ui-avatars URL দেয়, যেটা browser/player এ load হবে।
    """
    for stream in streams:
        existing = (stream.get('logo') or '').strip()
        if existing and existing.startswith('http'):
            continue  # ইতিমধ্যে logo আছে — পরিবর্তন না করি
        name = stream.get('name', 'IPTV')
        stream['logo'] = _build_avatar_url(name)
    return streams
