import re
import subprocess

import requests


def _label_from_width(width):
    if width >= 3840:
        return '4K'
    if width >= 2560:
        return '1440p'
    if width >= 1920:
        return '1080p'
    if width >= 1280:
        return '720p'
    if width >= 854:
        return '480p'
    return 'SD'


def detect_quality(target, timeout=10):
    if isinstance(target, (int, float)):
        return _label_from_width(int(target))

    url = target.get('url') if isinstance(target, dict) else str(target)
    if not url:
        return 'Unknown'

    if '.m3u8' in url.lower():
        try:
            text = requests.get(url, timeout=timeout, headers={'User-Agent': 'Mozilla/5.0'}).text
            widths = [int(match.split('x')[0]) for match in re.findall(r'RESOLUTION=(\d+x\d+)', text)]
            if widths:
                return _label_from_width(max(widths))
        except requests.RequestException:
            pass

    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width', '-of', 'default=nw=1:nk=1', url],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0 and result.stdout.strip().isdigit():
            return _label_from_width(int(result.stdout.strip()))
    except Exception:
        pass

    return 'Unknown'
