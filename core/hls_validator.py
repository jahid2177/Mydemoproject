import requests


HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) HLSValidator/1.0'}


def validate_hls(url, timeout=10):
    if not url or '.m3u8' not in url.lower():
        return False
    try:
        response = requests.get(url, timeout=timeout, headers=HEADERS)
        if response.status_code >= 400:
            return False
        text = response.text[:5000]
        return '#EXTM3U' in text and ('#EXT-X-' in text or '#EXTINF:' in text)
    except requests.RequestException:
        return False
