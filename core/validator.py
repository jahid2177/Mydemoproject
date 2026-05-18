
import requests

def is_alive(url):
    try:
        r = requests.get(url, timeout=10)
        return r.status_code == 200
    except:
        return False
