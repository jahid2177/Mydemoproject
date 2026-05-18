
import requests

def parse_xtream(server, username, password):
    url = f"{server}/player_api.php?username={username}&password={password}"
    return requests.get(url).json()
