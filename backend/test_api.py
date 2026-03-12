import requests

url = "http://127.0.0.1:5000/skin-tone"

file_path = r"C:\Users\manda\OneDrive\Desktop\face.jpg"

files = {
    "image": open(file_path, "rb")
}

response = requests.post(url, files=files)

print(response.json())