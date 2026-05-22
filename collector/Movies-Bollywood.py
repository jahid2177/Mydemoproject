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
    def __init__(self, country="Bollywood", base_dir="Movies"):
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

    def extract_stream_urls_from_html(self, html_content, base_url):
        if not html_content:
            return []
        soup = BeautifulSoup(html_content, 'html.parser')
        stream_urls = set()
        for link in soup.find_all('a', href=True):
            href = link['href']
            parsed_base = urlparse(base_url)
            parsed_href = urlparse(href)
            if not parsed_href.scheme:
                href = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
            if (href.endswith(('.m3u', '.m3u8')) or
                re.match(r'^https?://.*\.(ts|mp4|avi|mkv)$', href) or
                'playlist' in href.lower() or 'stream' in href.lower()):
                if not any(x in href.lower() for x in ['telegram', '.html', '.php', 'github.com', 'login']):
                    stream_urls.add(href)
        return list(stream_urls)

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
                group = group_match.group(1) if group_match else "Bollywood"
                
                # উন্নত Regex (কোমার ভেতরে থাকা নাম সঠিকভাবে ধরার জন্য)
                name_match = re.search(r'(?:^|")(?:[^"]*"),([^,].+)$', line)
                if not name_match:
                    name_match = re.search(r',([^,].+)$', line)
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
        logging.info(f"Checking {len(all_ch)} links...")
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
                except Exception as e:
                    logging.error(f"Error checking {ch['url']}: {e}")
        self.channels = active
        logging.info(f"Active links: {sum(len(v) for v in active.values())}")

    def process_sources(self, source_urls):
        self.channels.clear()
        self.seen_urls.clear()
        extra_m3u = set()
        for url in source_urls:
            content, lines = self.fetch_content(url)
            if url.endswith('.html'):
                extra_m3u.update(self.extract_stream_urls_from_html(content, url))
            elif lines:
                self.parse_and_store(lines, url)
                
        for u in extra_m3u:
            _, lines = self.fetch_content(u)
            if lines:
                self.parse_and_store(lines, u)
                
        if self.channels:
            self.filter_active_channels()
        else:
            logging.warning("No channels found across any sources!")

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
            "category": "Bollywood",
            "updated": datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S'),
            "total": sum(len(v) for v in self.channels.values()),
            "channels": dict(self.channels)
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logging.info(f"JSON saved: {path}")

    def export_app_json(self, filename="Movies_app.json"):
        path = os.path.join(self.output_dir, filename)
        items = []
        for group, chs in self.channels.items():
            for ch in chs:
                items.append({"name": ch['name'], "category": group, "url": ch['url'], "logo": ch['logo']})
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        logging.info(f"App JSON saved: {path}")


def main():
    sources = [
        "https://raw.githubusercontent.com/Mahabubulalammim/New/refs/heads/main/Mim%20New%20Movie%20Collection",
        "https://raw.githubusercontent.com/Mahabubulalammim/New/refs/heads/main/Mim-Movies.mim",
        "https://raw.githubusercontent.com/sm-monirulislam/SM-Live-TV/refs/heads/main/AynaOTT.m3u",
        "https://raw.githubusercontent.com/sm-monirulislam/SM-Live-TV/refs/heads/main/Combined_Live_TV.m3u",
        "https://raw.githubusercontent.com/imShakil/tvlink/refs/heads/main/all.m3u",
    ]
    
    collector = M3UCollector(country="Bollywood")
    collector.process_sources(sources)
    
    total = sum(len(v) for v in collector.channels.values())
    
    # যদি লিংকগুলো অন্তত ১টি কাজ করে, তবেই ফাইলগুলো সেভ হবে। 
    # এতে ভুলবশত পুরোনো কাজ করা লিংকগুলো ডিলেট হওয়া থেকে বাঁচবে।
    if total > 0:
        collector.export_m3u()
        collector.export_json()
        collector.export_app_json()
        logging.info(f"Done! Total Bollywood movies collected and saved: {total}")
    else:
        logging.error("No active Bollywood movies found! Skipping file generation to protect existing files.")

if __name__ == "__main__":
    main()
