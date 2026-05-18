import glob
import json
import os
import re
from typing import Dict, Iterable, List, Tuple

ATTRIBUTE_RE = re.compile(r'([\w-]+)="([^"]*)"')


def ensure_dir(path: str) -> None:
    directory = path if os.path.isdir(path) else os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def normalize_name(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', (value or '').lower()).strip()


def parse_attributes(extinf_line: str) -> Dict[str, str]:
    return {key: value for key, value in ATTRIBUTE_RE.findall(extinf_line or '')}


def parse_m3u_text(text: str, source: str = '', default_group: str = 'Uncategorized') -> Tuple[List[dict], List[str]]:
    entries: List[dict] = []
    epg_urls: List[str] = []
    current_info = None

    for raw_line in (text or '').splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith('#EXTM3U'):
            attrs = parse_attributes(line)
            if attrs.get('x-tvg-url'):
                epg_urls.extend([u.strip() for u in attrs['x-tvg-url'].split(',') if u.strip()])
            continue
        if line.startswith('#EXTINF'):
            current_info = line
            continue
        if line.startswith('#'):
            continue
        if current_info is None:
            current_info = '#EXTINF:-1,Unknown'

        attrs = parse_attributes(current_info)
        name = current_info.split(',', 1)[-1].strip() if ',' in current_info else 'Unknown'
        group = attrs.get('group-title') or default_group
        entry = {
            'name': name or 'Unknown',
            'logo': attrs.get('tvg-logo', '').strip(),
            'group': group.strip() if isinstance(group, str) else default_group,
            'url': line,
            'source': source,
            'epg_id': attrs.get('tvg-id', '').strip(),
            'epg_name': attrs.get('tvg-name', '').strip(),
            'extinf': current_info,
        }
        entries.append(entry)
        current_info = None

    return entries, epg_urls


def load_playlist_file(path: str, default_group: str = 'Uncategorized') -> Tuple[List[dict], List[str]]:
    with open(path, 'r', encoding='utf-8', errors='ignore') as handle:
        return parse_m3u_text(handle.read(), source=path, default_group=default_group)


def build_extinf(entry: dict) -> str:
    attrs = []
    if entry.get('epg_id'):
        attrs.append(f'tvg-id="{entry["epg_id"]}"')
    if entry.get('epg_name'):
        attrs.append(f'tvg-name="{entry["epg_name"]}"')
    if entry.get('logo'):
        attrs.append(f'tvg-logo="{entry["logo"]}"')
    if entry.get('group'):
        attrs.append(f'group-title="{entry["group"]}"')
    attr_text = (' ' + ' '.join(attrs)) if attrs else ''
    return f'#EXTINF:-1{attr_text},{entry.get("name", "Unknown")}'


def write_m3u(path: str, entries: Iterable[dict], epg_urls: Iterable[str] = ()) -> None:
    ensure_dir(path)
    unique_epg = [u for u in dict.fromkeys(epg_urls or []) if u]
    header = '#EXTM3U'
    if unique_epg:
        header += f' x-tvg-url="{",".join(unique_epg)}"'
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(header + '\n')
        for entry in entries:
            handle.write(build_extinf(entry) + '\n')
            handle.write((entry.get('url') or '').strip() + '\n')


def write_json(path: str, data) -> None:
    ensure_dir(path)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


def discover_local_playlists(base_dir: str = '.') -> List[str]:
    patterns = [
        os.path.join(base_dir, 'data', 'input', '*.m3u'),
        os.path.join(base_dir, 'Movies', '*', 'Movies.m3u'),
        os.path.join(base_dir, 'LiveTV', '*.m3u'),
    ]
    paths = []
    for pattern in patterns:
        paths.extend(glob.glob(pattern))
    return sorted({os.path.normpath(path) for path in paths if os.path.isfile(path)})


def classify_entry(entry: dict) -> str:
    text = f"{entry.get('name', '')} {entry.get('group', '')} {entry.get('url', '')}".lower()
    keywords = [' tv', 'news', 'sport', 'channel', 'live', '/live', '.ts', '.m3u8']
    return 'tv' if any(keyword in text for keyword in keywords) else 'movie'
