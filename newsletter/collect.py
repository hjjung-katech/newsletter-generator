import requests
import json
from . import config

def collect_articles(keywords: str):
    """
    Collect articles from Serper.dev based on keywords.
    """
    print(f"Collecting articles for: {keywords} using Serper.dev")
    # 키워드별 기사 수를 저장할 딕셔너리
    keyword_article_counts = {}

    if not config.SERPER_API_KEY:
        print("Error: SERPER_API_KEY not found. Please set it in the .env file.")
        return []

    url = "https://google.serper.dev/search"

    # 각 키워드에 대해 개별적으로 API 호출
    individual_keywords = [kw.strip() for kw in keywords.split(',')]
    all_articles = []

    for keyword in individual_keywords:
        print(f"Searching for keyword: {keyword}")
        payload = json.dumps({
            "q": keyword,
            "num": 10  # Number of results to return per keyword
        })
        headers = {
            'X-API-KEY': config.SERPER_API_KEY,
            'Content-Type': 'application/json'
        }

        try:
            response = requests.request("POST", url, headers=headers, data=payload)
            response.raise_for_status()  # Raise an exception for HTTP errors
            search_results = response.json()
            
            articles_for_keyword = []
            if "organic" in search_results:
                for item in search_results["organic"]:
                    articles_for_keyword.append({
                        "title": item.get("title", "No Title"),
                        "url": item.get("link", "#"),
                        "content": item.get("snippet", "No Content Snippet") 
                    })
            
            # 키워드별 기사 수 저장 및 출력
            num_articles_found = len(articles_for_keyword)
            keyword_article_counts[keyword] = num_articles_found
            print(f"Found {num_articles_found} articles for keyword: '{keyword}'")
            
            all_articles.extend(articles_for_keyword)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching articles for keyword '{keyword}' from Serper.dev: {e}")
        except json.JSONDecodeError:
            print(f"Error decoding JSON response for keyword '{keyword}' from Serper.dev. Response: {response.text}")

    # 전체 수집된 기사 수 출력
    print(f"\nTotal collected articles: {len(all_articles)}")
    # 키워드별 수집된 기사 수 요약 출력
    print("Summary of articles collected per keyword:")
    for kw, count in keyword_article_counts.items():
        print(f"- '{kw}': {count} articles")
        
    return all_articles

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
