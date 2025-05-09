"""
Newsletter Generator - Custom Tools
이 모듈은 뉴스레터 생성을 위한 LangChain 도구를 정의합니다.
"""
from langchain.tools import tool
from langchain_core.tools import ToolException
import requests
import json
import os
from bs4 import BeautifulSoup
import markdownify
from typing import Dict, List, Any, Optional
from . import config

@tool
def search_news_articles(keywords: str, num_results: int = 10) -> List[Dict]:
    """
    Search for news articles using the Serper.dev API.
    
    Args:
        keywords: Keywords to search for, like 'AI in healthcare'
        num_results: Number of results to return (default: 10, max: 20)
    
    Returns:
        A list of article dictionaries with 'title', 'url', and 'snippet' keys.
    """
    if not config.SERPER_API_KEY:
        raise ToolException("SERPER_API_KEY not found. Please set it in the .env file.")
    
    if num_results > 20:
        num_results = 20  # Limit to 20 results max
      url = "https://google.serper.dev/search"
    payload = json.dumps({
        "q": keywords,
        "gl": "kr",  # 한국 지역 결과
        "hl": "ko",  # 한국어 결과
        "num": num_results
    })
    headers = {
        'X-API-KEY': config.SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        response.raise_for_status()
        
        results = response.json()
        articles = []
        
        # 검색 결과에서 기사 정보 추출
        if "organic" in results:
            for item in results["organic"]:
                article = {
                    "title": item.get("title", "제목 없음"),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", "내용 없음")
                }
                articles.append(article)
        
        return articles
    except requests.exceptions.RequestException as e:
        raise ToolException(f"Error fetching articles from Serper.dev: {e}")
    except json.JSONDecodeError:
        raise ToolException(f"Error decoding JSON response from Serper.dev. Response: {response.text}")

@tool
def fetch_article_content(url: str) -> Dict[str, Any]:
    """
    Fetch the full content of an article from its URL.
    
    Args:
        url: The URL of the article to fetch
        
    Returns:
        A dictionary with 'title', 'url', and 'content' keys
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 타이틀 추출
        title = soup.title.text.strip() if soup.title else "제목 없음"
        
        # 메인 콘텐츠 추출 시도 (다양한 방법으로)
        content = ""
        
        # 메타 설명 추출
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            content += meta_desc.get('content') + "\n\n"
        
        # article 태그 찾기
        article_tag = soup.find('article')
        if article_tag:
            # 불필요한 요소 제거
            for tag in article_tag.find_all(['script', 'style', 'nav', 'footer', 'aside']):
                tag.decompose()
            
            content += article_tag.get_text(separator='\n', strip=True)
        else:
            # 본문으로 추정되는 태그들 찾기
            for tag_name in ['div', 'section']:
                for attr in ['id', 'class']:
                    for keyword in ['content', 'article', 'main', 'body', 'entry', 'post']:
                        main_content = soup.find(tag_name, {attr: lambda x: x and keyword in x.lower() if x else False})
                        if main_content:
                            # 불필요한 요소 제거
                            for tag in main_content.find_all(['script', 'style', 'nav', 'footer', 'aside']):
                                tag.decompose()
                            
                            content += main_content.get_text(separator='\n', strip=True)
                            break
                    if content:
                        break
                if content:
                    break
        
        # 본문을 찾지 못한 경우 전체 텍스트 사용
        if not content:
            # 불필요한 요소 제거
            for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'aside']):
                tag.decompose()
                
            content = soup.body.get_text(separator='\n', strip=True) if soup.body else "내용을 추출할 수 없습니다."
        
        # 결과 반환
        return {
            "title": title,
            "url": url,
            "content": content[:5000]  # 컨텐츠 길이 제한 (토큰 절약)
        }
        
    except Exception as e:
        raise ToolException(f"Error fetching article content: {str(e)}")

@tool
def save_newsletter_locally(html_content: str, filename_base: str, output_format: str = "html") -> str:
    """
    Save newsletter content locally as HTML or Markdown.
    
    Args:
        html_content: HTML content of the newsletter
        filename_base: Base filename (without extension)
        output_format: Format to save as ('html' or 'md')
    
    Returns:
        Path to the saved file
    """
    if output_format not in ['html', 'md']:
        raise ToolException("Format must be 'html' or 'md'")
        
    try:
        # 출력 디렉토리 생성 (없는 경우)
        output_dir = os.path.join(os.getcwd(), 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        # 파일 경로 생성
        file_path = os.path.join(output_dir, f"{filename_base}.{output_format}")
        
        # 마크다운으로 변환 (필요한 경우)
        if output_format == 'md':
            content = markdownify.markdownify(html_content, heading_style="ATX")
        else:
            content = html_content
        
        # 파일 저장
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
              return f"Newsletter saved locally as {filename_base}.{output_format} at {file_path}"
            
    except Exception as e:
        raise ToolException(f"Error saving newsletter: {str(e)}")
        raise ToolException(f"Error saving newsletter locally: {e}")
