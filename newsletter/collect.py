import requests
import json
from . import config

def collect_articles(keywords: str):
    """
    Collect articles from Serper.dev based on keywords.
    """
    print(f"Collecting articles for: {keywords} using Serper.dev")
    if not config.SERPER_API_KEY:
        print("Error: SERPER_API_KEY not found. Please set it in the .env file.")
        return []

    url = "https://google.serper.dev/search"
    payload = json.dumps({
        "q": keywords,
        "num": 10  # Number of results to return
    })
    headers = {
        'X-API-KEY': config.SERPER_API_KEY,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors
        search_results = response.json()
        
        articles = []
        if "organic" in search_results:
            for item in search_results["organic"]:
                articles.append({
                    "title": item.get("title", "No Title"),
                    "url": item.get("link", "#"),
                    "content": item.get("snippet", "No Content Snippet") 
                })
        return articles
    except requests.exceptions.RequestException as e:
        print(f"Error fetching articles from Serper.dev: {e}")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON response from Serper.dev. Response: {response.text}")
        return []

if __name__ == '__main__':
    # Example usage:
    # Make sure to have SERPER_API_KEY in your .env file
    # from config import SERPER_API_KEY # For direct execution test
    # if not SERPER_API_KEY:
    #     print("Please set SERPER_API_KEY in .env file for testing.")
    # else:
    #     test_keywords = "AI in healthcare"
    #     collected_articles = collect_articles(test_keywords)
    #     if collected_articles:
    #         print(f"\nCollected {len(collected_articles)} articles for '{test_keywords}':")
    #         for article in collected_articles:
    #             print(f"- Title: {article['title']}")
    #             print(f"  URL: {article['url']}")
    #             print(f"  Snippet: {article['content'][:100]}...") # Print first 100 chars of snippet
    #     else:
    #         print(f"No articles collected for '{test_keywords}'.")
    pass
