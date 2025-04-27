import requests

NEWS_API_KEY = "11678158200b43e991b712fb9c11b284"

def fetch_stock_news():
    url = (
        f"https://newsapi.org/v2/everything?"
        f"q=stock market&language=en&sortBy=publishedAt&pageSize=5&"
        f"apiKey={NEWS_API_KEY}"
    )

    try:
        response = requests.get(url)
        data = response.json()

        articles = []
        if data.get("status") == "ok":
            for article in data["articles"]:
                articles.append({
                    "title": article["title"],
                    "url": article["url"],
                    "source": article["source"]["name"],
                    "published": article["publishedAt"],
                    "description": article["description"]
                })
        return articles
    except Exception as e:
        print("Error fetching news:", e)
        return []
