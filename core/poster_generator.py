import html
import os
import re


def _safe_filename(value):
    cleaned = re.sub(r'[^A-Za-z0-9._-]+', '_', value.strip())
    return cleaned[:80] or 'poster'


def fetch_poster(movie, output_dir='assets/posters'):
    os.makedirs(output_dir, exist_ok=True)
    title = movie.get('name') if isinstance(movie, dict) else str(movie)
    group = movie.get('group', 'IPTV') if isinstance(movie, dict) else 'IPTV'
    filename = _safe_filename(title) + '.svg'
    path = os.path.join(output_dir, filename)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="600" height="900" viewBox="0 0 600 900">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#1f2937"/>
      <stop offset="100%" stop-color="#7c3aed"/>
    </linearGradient>
  </defs>
  <rect width="600" height="900" fill="url(#bg)" rx="32"/>
  <text x="50%" y="18%" text-anchor="middle" fill="#ffffff" font-size="34" font-family="Arial">Poster Generator</text>
  <text x="50%" y="45%" text-anchor="middle" fill="#ffffff" font-size="54" font-weight="bold" font-family="Arial">{html.escape(title)}</text>
  <text x="50%" y="55%" text-anchor="middle" fill="#d1d5db" font-size="28" font-family="Arial">{html.escape(group)}</text>
  <text x="50%" y="88%" text-anchor="middle" fill="#cbd5e1" font-size="22" font-family="Arial">Generated locally without external API</text>
</svg>'''
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(svg)
    return path
