import requests
import json
import os
import re
from urllib.parse import urlparse
from collections import defaultdict
from datetime import datetime
import pytz
import concurrent.futures
import threading
import logging
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class M3UCollector:
    def __init__(self, country="Hollywood", base_dir="Movies"):
        self.channels = defaultdict(list)
        self.default_logo = "https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/logo/default-logo.png"
        self.seen_urls = set()
        self.output_dir = os.path.join(base_dir, country)
        self.lock = threading.Lock()
        os.makedirs(self.output_dir, exist_ok=True)

    def fetch_content(self, url):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        try:
            with requests.get(url, stream=True, headers=headers, timeout=15) as response:
                response.raise_for_status()
                lines = [line.decode('utf-8', errors='ignore') if isinstance(line, bytes) else line
                         for line in response.iter_lines()]
                content = '\n'.join(lines)
                logging.info(f"Fetched {len(lines)} lines from {url}")
                return content, lines
        except requests.RequestException as e:
            logging.error(f"Failed to fetch {url}: {e}")
            return None, []

    def check_link_active(self, url, timeout=5):
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            response = requests.head(url, timeout=timeout, headers=headers, allow_redirects=True)
            return response.status_code < 400
        except:
            try:
                with requests.get(url, stream=True, timeout=timeout, headers=headers) as r:
                    return r.status_code < 400
            except:
                return False

    def parse_and_store(self, lines, source_url):
        current_channel = {}
        count = 0
        for line in lines:
            line = line.strip()
            if line.startswith('#EXTINF:'):
                logo_match = re.search(r'tvg-logo="([^"]*)"', line)
                logo = logo_match.group(1) if logo_match and logo_match.group(1) else self.default_logo
                group_match = re.search(r'group-title="([^"]*)"', line)
                group = group_match.group(1) if group_match else "Hollywood"
                name_match = re.search(r',(.+)$', line)
                name = name_match.group(1).strip() if name_match else "Unknown"
                current_channel = {'name': name, 'logo': logo, 'group': group, 'source': source_url}
            elif line.startswith('http') and current_channel:
                with self.lock:
                    if line not in self.seen_urls:
                        self.seen_urls.add(line)
                        current_channel['url'] = line
                        self.channels[current_channel['group']].append(current_channel)
                        count += 1
                current_channel = {}
        logging.info(f"Parsed {count} entries from {source_url}")

    def filter_active_channels(self):
        active = defaultdict(list)
        all_ch = [(g, ch) for g, chs in self.channels.items() for ch in chs]
        seen = set()
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = {
                executor.submit(self.check_link_active, ch['url']): (g, ch)
                for g, ch in all_ch if ch['url'] not in seen and not seen.add(ch['url'])
            }
            for future in concurrent.futures.as_completed(futures):
                g, ch = futures[future]
                try:
                    if future.result():
                        active[g].append(ch)
                except:
                    pass
        self.channels = active

    def process_sources(self, source_urls):
        self.channels.clear()
        self.seen_urls.clear()
        for url in source_urls:
            _, lines = self.fetch_content(url)
            self.parse_and_store(lines, url)
        if self.channels:
            self.filter_active_channels()

    def export_m3u(self, filename="Movies.m3u"):
        path = os.path.join(self.output_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write('#EXTM3U\n')
            for group, chs in self.channels.items():
                for ch in chs:
                    f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}" group-title="{group}",{ch["name"]}\n')
                    f.write(f'{ch["url"]}\n')
        logging.info(f"M3U saved: {path}")

    def export_json(self, filename="Movies.json"):
        path = os.path.join(self.output_dir, filename)
        tz = pytz.timezone('Asia/Dhaka')
        data = {
            "category": "Hollywood",
            "updated": datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S'),
            "total": sum(len(v) for v in self.channels.values()),
            "channels": dict(self.channels)
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def export_app_json(self, filename="Movies_app.json"):
        path = os.path.join(self.output_dir, filename)
        items = []
        for group, chs in self.channels.items():
            for ch in chs:
                items.append({"name": ch['name'], "category": group, "url": ch['url'], "logo": ch['logo']})
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)


def main():
    sources = [
        "https://raw.githubusercontent.com/BrianRVP/Bflix34567/refs/heads/main/Marvel",
        "https://raw.githubusercontent.com/BrianRVP/Bflix34567/refs/heads/main/Fantas%C3%ADa",
        "https://raw.githubusercontent.com/BrianRVP/Bflix34567/refs/heads/main/Max",
        "https://raw.githubusercontent.com/BrianRVP/Bflix34567/refs/heads/main/Neflix",
        "https://raw.githubusercontent.com/BrianRVP/Bflix34567/refs/heads/main/Paramount",
        "https://raw.githubusercontent.com/BrianRVP/Bflix34567/refs/heads/main/Romance",
        "https://raw.githubusercontent.com/BrianRVP/Bflix34567/refs/heads/main/Star",
        "https://raw.githubusercontent.com/BrianRVP/Bflix34567/refs/heads/main/Terror",
        "https://raw.githubusercontent.com/clseibold/tubi-m3u/refs/heads/main/tubi_playlist_us.m3u",
        "https://raw.githubusercontent.com/HelmerLuzo/PlutoTV_HL/refs/heads/main/tv/m3u/PlutoTV_tv_US.m3u",
    ]
    collector = M3UCollector(country="Hollywood")
    collector.process_sources(sources)
    collector.export_m3u()
    collector.export_json()
    collector.export_app_json()
    total = sum(len(v) for v in collector.channels.values())
    logging.info(f"Done! Total Hollywood movies collected: {total}")

if __name__ == "__main__":
    main()
