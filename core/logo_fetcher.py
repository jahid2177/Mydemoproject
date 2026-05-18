from urllib.parse import quote_plus

DEFAULT_LOGO = 'https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/logo/default-logo.png'


def fetch_logo(channel_name):
    name = (channel_name or 'IPTV').strip()
    return f'https://ui-avatars.com/api/?name={quote_plus(name)}&background=0D8ABC&color=fff&size=256&bold=true'


def apply_logos(streams, default_logo=DEFAULT_LOGO):
    for stream in streams:
        stream['logo'] = (stream.get('logo') or '').strip() or fetch_logo(stream.get('name')) or default_logo
    return streams
