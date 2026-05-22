import requests
import json
import os
import re
from collections import defaultdict
from datetime import datetime
import pytz
import concurrent.futures
import threading
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BLOCKED_DOMAINS = ['drive.google.com', 'dropbox.com', 'mega.nz', 'youtube.com']

def is_valid_stream_url(url):
    if not url.startswith("http"):
        return False
    for domain in BLOCKED_DOMAINS:
        if domain in url:
            return False
    return True

class M3UCollector:
    def __init__(self, country="Bengali", base_dir="Movies"):
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
                logging.info(f"Fetched {len(lines)} lines from {url}")
                return '\n'.join(lines), lines
        except requests.RequestException as e:
            logging.error(f"Failed: {url} -> {e}")
            return None, []

    def check_link_active(self, url, timeout=5):
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            r = requests.head(url, timeout=timeout, headers=headers, allow_redirects=True)
            return r.status_code < 400
        except:
            try:
                with requests.get(url, stream=True, timeout=timeout, headers=headers) as r:
                    return r.status_code < 400
            except:
                return False

    def parse_and_store(self, lines, source_url):
        current_info = {}
        count = 0
        for line in lines:
            line = line.strip()
            if line.startswith('#EXTINF:'):
                logo = re.search(r'tvg-logo="([^"]*)"', line)
                group = re.search(r'group-title="([^"]*)"', line)
                name_match = re.search(r'(?:^|")(?:[^"]*"),([^,].+)$', line)
                if not name_match:
                    name_match = re.search(r',([^,].+)$', line)
                name = name_match.group(1).strip() if name_match else "Unknown"
                current_info = {
                    'name': name,
                    'logo': logo.group(1) if logo and logo.group(1) else self.default_logo,
                    'group': group.group(1) if group else "Bengali Movies",
                    'source': source_url
                }
            elif line.startswith('http') and current_info:
                if is_valid_stream_url(line):
                    with self.lock:
                        if line not in self.seen_urls:
                            self.seen_urls.add(line)
                            current_info['url'] = line
                            self.channels[current_info['group']].append(current_info)
                            count += 1
                current_info = {} # পরবর্তী লাইনের জন্য রিসেট
        return count

    def save_files(self):
        m3u_path = os.path.join(self.output_dir, "Movies.m3u")
        json_path = os.path.join(self.output_dir, "Movies.json")
        app_json_path = os.path.join(self.output_dir, "Movies_app.json")
        
        # M3U সেভ করা
        with open(m3u_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for group, channels in self.channels.items():
                for ch in channels:
                    f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}" group-title="{group}",{ch["name"]}\n')
                    f.write(f'{ch["url"]}\n')
        
        # JSON সেভ করা
        all_channels = []
        for group, channels in self.channels.items():
            all_channels.extend(channels)
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(all_channels, f, indent=4, ensure_ascii=False)
            
        # Movies_app.json সেভ করা
        with open(app_json_path, "w", encoding="utf-8") as f:
            json.dump({"movies": all_channels}, f, indent=4, ensure_ascii=False)
            
        logging.info(f"Files saved successfully in {self.output_dir}/")
        return len(all_channels)

if __name__ == "__main__":
    # ⚠️ আপনার সোর্স লিঙ্কগুলো এখানে দিন (নিচের লিঙ্কটি মুছে আপনারগুলো বসান)
    SOURCES = [
        "https://example.com/your-source-url-here.m3u" 
    ]
    
    collector = M3UCollector(country="Bengali", base_dir="Movies")
    
    total_found = 0
    for source in SOURCES:
        content, lines = collector.fetch_content(source)
        if lines:
            count = collector.parse_and_store(lines, source)
            total_found += count
            logging.info(f"Parsed {count} new movies from {source}")
            
    if total_found > 0:
        collector.save_files()
    else:
        logging.warning("No movies found. Files will not be generated.")
