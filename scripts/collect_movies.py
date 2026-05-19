import json
  import requests
  import threading
  from concurrent.futures import ThreadPoolExecutor

  SOURCES = [
      "https://raw.githubusercontent.com/time2shine/IPTV/refs/heads/master/scripts/static_movies(103.225.94.27).json",
      "https://raw.githubusercontent.com/time2shine/IPTV/refs/heads/master/scripts/static_movies(cinehub24).json",
      "https://raw.githubusercontent.com/time2shine/IPTV/refs/heads/master/scripts/static_movies(ctgfun).json",
      "https://raw.githubusercontent.com/time2shine/IPTV/refs/heads/master/scripts/static_movies(discoveryftp).json"
  ]

  movies = []
  duplicate_movies = []
  seen_links = set()
  lock = threading.Lock()


  def extract_link(item):
      if isinstance(item, str):
          if item.startswith("http"):
              return item
          return None

      if isinstance(item, dict):
          item_lower = {str(k).lower(): v for k, v in item.items()}
          keys = ["url", "link", "stream_url", "video_url", "file", "movie_url", "path", "stream"]
          for key in keys:
              if key in item_lower and isinstance(item_lower[key], str):
                  val = item_lower[key]
                  if val.startswith("http"):
                      return val
      return None


  def process_movie(item):
      link = extract_link(item)
      if not link:
          return
      with lock:
          if link in seen_links:
              duplicate_movies.append(item)
              return
          seen_links.add(link)
          movies.append(item)


  for source in SOURCES:
      try:
          print(f"\nFetching: {source}")
          response = requests.get(source, timeout=30)
          response.raise_for_status()

          data = response.json()

          if isinstance(data, dict):
              extracted = data.get("movies", data.get("data", data.get("Movies", None)))
              if extracted is not None:
                  data = extracted
              else:
                  items = []
                  for title, movie in data.items():
                      if isinstance(movie, dict) and "links" in movie:
                          for link_obj in movie["links"]:
                              if isinstance(link_obj, dict):
                                  link_obj["title"] = title
                                  items.append(link_obj)
                  data = items

          if not isinstance(data, list) or len(data) == 0:
              print("Warning: Data is empty or not a list. Skipping this source.")
              continue

          print(f"Success: Found {len(data)} items to process in this source.")

          with ThreadPoolExecutor(max_workers=20) as executor:
              list(executor.map(process_movie, data))

      except requests.exceptions.RequestException as e:
          print(f"Network Error: {e}")
      except Exception as e:
          print(f"Unexpected Error: {e}")

  print("\n---------------------------------")
  print("Saving Files...")

  with open("movies_link.json", "w", encoding="utf-8") as f:
      json.dump(movies, f, indent=4, ensure_ascii=False)

  with open("duplicate_link.json", "w", encoding="utf-8") as f:
      json.dump(duplicate_movies, f, indent=4, ensure_ascii=False)

  print("Done")
  print(f"Movies: {len(movies)}")
  print(f"Duplicate: {len(duplicate_movies)}")
  