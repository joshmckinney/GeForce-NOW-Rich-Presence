import requests
import json

url = "https://api.github.com/repos/KarmaDevz/GeForce-NOW-Rich-Presence/releases/latest"
response = requests.get(url)
data = response.json()

print(json.dumps(data, indent=4))
