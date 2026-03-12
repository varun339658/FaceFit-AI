import requests

SERP_API_KEY = "c7b18af01ffb9d2c0a059c83ec8153e67debf8983e11ad16f8f41cf01e997586"
AFFILIATE_TAG = "facefitai21-20"


def get_product_recommendations(query):

    url = "https://serpapi.com/search.json"

    params = {
        "engine": "amazon",
        "amazon_domain": "amazon.in",
        "k": query,   # IMPORTANT: use k not q
        "api_key": SERP_API_KEY
    }

    response = requests.get(url, params=params)
    data = response.json()

    products = []

    if "organic_results" in data:

        for item in data["organic_results"][:5]:

            link = item.get("link")

            if link:
                if "?" in link:
                    link += "&tag=" + AFFILIATE_TAG
                else:
                    link += "?tag=" + AFFILIATE_TAG

            products.append({
                "title": item.get("title"),
                "price": item.get("price"),
                "image": item.get("thumbnail"),
                "link": link
            })

    print("SERP DATA:", data)   # debug

    return products