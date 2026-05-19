"""
HLS Validator
✅ FIX: redirect handle করে
✅ FIX: partial/chunked response এও valid detect করে
✅ FIX: Content-Type header দিয়েও validate করে
"""
import requests

HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) HLSValidator/1.0'}

HLS_CONTENT_TYPES = {
    'application/vnd.apple.mpegurl',
    'application/x-mpegurl',
    'audio/mpegurl',
    'audio/x-mpegurl',
}


def validate_hls(url: str, timeout: int = 10) -> bool:
    """
    URL টি valid HLS stream কিনা পরীক্ষা করে।
    Returns True যদি:
      - Content-Type HLS content type হয়, অথবা
      - Response body তে #EXTM3U এবং #EXT-X- / #EXTINF: থাকে
    """
    if not url or '.m3u8' not in url.lower():
        return False

    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={**HEADERS, 'Range': 'bytes=0-4096'},
            allow_redirects=True,
            stream=True,
        )
        if response.status_code >= 400:
            return False

        # Content-Type দিয়ে check
        content_type = response.headers.get('Content-Type', '').lower().split(';')[0].strip()
        if content_type in HLS_CONTENT_TYPES:
            return True

        # Body দিয়ে check — প্রথম 5KB যথেষ্ট
        text = ''
        for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
            if isinstance(chunk, bytes):
                try:
                    chunk = chunk.decode('utf-8', errors='ignore')
                except Exception:
                    continue
            text += chunk
            if len(text) >= 5000:
                break

        has_header = '#EXTM3U' in text
        has_tags = '#EXT-X-' in text or '#EXTINF:' in text
        return has_header and has_tags

    except requests.RequestException:
        return False
