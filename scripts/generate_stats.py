import json
  import os
  from datetime import datetime, timezone
  import pytz

  DHAKA_TZ = pytz.timezone('Asia/Dhaka')
  BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

  def count_json(path):
      try:
          with open(path, 'r', encoding='utf-8') as f:
              data = json.load(f)
          if isinstance(data, list):
              return len(data)
          if isinstance(data, dict):
              channels = data.get('channels', {})
              if channels:
                  return sum(len(v) for v in channels.values())
              return data.get('total', 0)
      except Exception:
          return 0

  def count_m3u(path):
      try:
          with open(path, 'r', encoding='utf-8', errors='ignore') as f:
              return sum(1 for line in f if line.strip().startswith('http'))
      except Exception:
          return 0

  def read_report(path):
      result = {}
      try:
          with open(path, 'r', encoding='utf-8') as f:
              for line in f:
                  if ':' in line:
                      key, _, val = line.partition(':')
                      try:
                          result[key.strip()] = int(val.strip())
                      except ValueError:
                          pass
      except Exception:
          pass
      return result

  def main():
      now_utc = datetime.now(timezone.utc)
      now_dhaka = now_utc.astimezone(DHAKA_TZ)

      categories = ['Bengali', 'Bollywood', 'Hollywood', 'SouthIndian', 'WorldwideVOD']
      cat_stats = {}
      total_all = 0

      for cat in categories:
          json_path = os.path.join(BASE_DIR, 'Movies', cat, 'Movies.json')
          m3u_path  = os.path.join(BASE_DIR, 'Movies', cat, 'Movies.m3u')

          json_count = count_json(json_path)
          m3u_count  = count_m3u(m3u_path)
          count      = json_count if json_count > 0 else m3u_count

          modified = None
          for p in [json_path, m3u_path]:
              if os.path.exists(p):
                  ts = os.path.getmtime(p)
                  dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(DHAKA_TZ)
                  modified = dt.strftime('%Y-%m-%d %H:%M:%S +0600')
                  break

          cat_stats[cat] = {
              'total': count,
              'last_updated': modified or 'N/A'
          }
          total_all += count

      movies_link_path    = os.path.join(BASE_DIR, 'movies_link.json')
      duplicate_link_path = os.path.join(BASE_DIR, 'duplicate_link.json')
      movies_link_count    = count_json(movies_link_path)
      duplicate_link_count = count_json(duplicate_link_path)

      all_movies_path    = os.path.join(BASE_DIR, 'all_movies.json')
      offline_movie_path = os.path.join(BASE_DIR, 'offline_movie.json')
      live_tv_path       = os.path.join(BASE_DIR, 'LiveTV', 'live_tv.json')
      offline_tv_path    = os.path.join(BASE_DIR, 'LiveTV', 'offline_tv.json')
      proc_report        = read_report(os.path.join(BASE_DIR, 'logs', 'processor_report.txt'))

      stats = {
          "last_updated_utc":   now_utc.strftime('%Y-%m-%d %H:%M:%S UTC'),
          "last_updated_dhaka": now_dhaka.strftime('%Y-%m-%d %H:%M:%S +0600'),
          "categories": cat_stats,
          "total_category_movies": total_all,
          "movies_link": {
              "unique":     movies_link_count,
              "duplicates": duplicate_link_count
          },
          "processor": {
              "online_movies":  count_json(all_movies_path),
              "offline_movies": count_json(offline_movie_path),
              "online_tv":      count_json(live_tv_path),
              "offline_tv":     count_json(offline_tv_path),
              "report":         proc_report
          },
          "grand_total": total_all + movies_link_count
      }

      out_path = os.path.join(BASE_DIR, 'stats.json')
      with open(out_path, 'w', encoding='utf-8') as f:
          json.dump(stats, f, indent=2, ensure_ascii=False)

      print("===== STATS =====")
      print(f"Last updated : {stats['last_updated_dhaka']}")
      print(f"Grand total  : {stats['grand_total']} movies")
      for cat, info in cat_stats.items():
          print(f"  {cat:<15}: {info['total']}")
      print(f"  movies_link  : {movies_link_count} unique, {duplicate_link_count} duplicates")
      print(f"  Processor    : {stats['processor']['online_movies']} online movies")
      print(f"  Live TV      : {stats['processor']['online_tv']} online channels")
      print(f"Stats saved: {out_path}")

  if __name__ == '__main__':
      main()
  