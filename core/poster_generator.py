
import requests

TMDB_API_KEY = "YOUR_API_KEY"

def fetch_poster(movie):
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie}"
    return requests.get(url).json()
