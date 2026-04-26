import requests

url = "http://127.0.0.1:5000/outfits"

data = {
    "face_shape": "oval",
    "skin_tone": {
        "skin_tone": "medium"
    }
}

response = requests.post(url, json=data)

print(response.json())