"""
Stream Quality Detector
✅ FIX: ffprobe না থাকলে gracefully fallback করে
✅ FIX: HLS playlist থেকে RESOLUTION parse করে quality নির্ধারণ করে
✅ FIX: Optional[str] ব্যবহার করা হয়েছে — Python 3.9 compatible (str | None ছিল 3.10+ only)
"""
import re
import shutil
import subprocess
from typing import Optional

import requests

HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) QualityDetector/1.0'}
FFPROBE_AVAILABLE = shutil.which('ffprobe') is not None


def _label_from_width(width: int) -> str:
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


def _quality_from_hls_playlist(url: str, timeout: int = 10) -> Optional[str]:
    """
    M3U8 playlist fetch করে RESOLUTION= tag থেকে quality বের করে।
    ✅ FIX: Optional[str] — Python 3.9 compatible
    """
    try:
        resp = requests.get(url, timeout=timeout, headers=HEADERS)
        if resp.status_code >= 400:
            return None
        text = resp.text[:8000]
        widths = [
            int(m.split('x')[0])
            for m in re.findall(r'RESOLUTION=(\d+x\d+)', text)
        ]
        if widths:
            return _label_from_width(max(widths))

        # Single-bitrate stream — BANDWIDTH থেকে estimate
        bandwidths = [int(b) for b in re.findall(r'BANDWIDTH=(\d+)', text)]
        if bandwidths:
            bw = max(bandwidths)
            if bw >= 8_000_000:
                return '1080p'
            if bw >= 4_000_000:
                return '720p'
            if bw >= 1_500_000:
                return '480p'
            return 'SD'
    except requests.RequestException:
        pass
    return None


def _quality_from_ffprobe(url: str, timeout: int = 10) -> Optional[str]:
    """
    ffprobe দিয়ে video width বের করে — ffprobe না থাকলে None।
    ✅ FIX: Optional[str] — Python 3.9 compatible
    """
    if not FFPROBE_AVAILABLE:
        return None
    try:
        result = subprocess.run(
            [
                'ffprobe', '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width',
                '-of', 'default=nw=1:nk=1',
                url,
            ],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode == 0 and result.stdout.strip().isdigit():
            return _label_from_width(int(result.stdout.strip()))
    except Exception:
        pass
    return None


def detect_quality(target, timeout: int = 10) -> str:
    """
    Stream এর quality detect করে।
    target: stream dict অথবা URL string অথবা width (int/float)।
    Returns: '4K' | '1440p' | '1080p' | '720p' | '480p' | 'SD' | 'Unknown'
    """
    # Numeric width directly দেওয়া থাকলে
    if isinstance(target, (int, float)):
        return _label_from_width(int(target))

    url = target.get('url') if isinstance(target, dict) else str(target)
    if not url:
        return 'Unknown'

    # HLS stream → playlist parse করি
    if '.m3u8' in url.lower():
        result = _quality_from_hls_playlist(url, timeout)
        if result:
            return result

    # ffprobe fallback (যদি available থাকে)
    result = _quality_from_ffprobe(url, timeout)
    if result:
        return result

    return 'Unknown'
