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
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from . import config
from rich.console import Console

console = Console()

@tool
def search_news_articles(keywords: str, num_results: int = 10) -> List[Dict]:
    """
    Search for news articles using the Serper.dev API for each keyword.
    
    Args:
        keywords: Comma-separated keywords to search for, like 'AI,Machine Learning'
        num_results: Number of results to return per keyword (default: 10, max: 20)
    
    Returns:
        A list of article dictionaries with 'title', 'url', and 'snippet' keys.
    """
    if not config.SERPER_API_KEY:
        raise ToolException("SERPER_API_KEY not found. Please set it in the .env file.")
    
    if num_results > 20:
        num_results = 20  # Limit to 20 results max

    individual_keywords = [kw.strip() for kw in keywords.split(',')]
    all_collected_articles = []
    keyword_article_counts = {}

    print("\nStarting article collection process:")
    for keyword in individual_keywords:
        print(f"Searching articles for keyword: '{keyword}'")
        url = "https://google.serper.dev/search"
        payload = json.dumps({
            "q": keyword, # Search for individual keyword
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
            articles_for_keyword = []
            
            if "organic" in results:
                for item_idx, item in enumerate(results["organic"]): # 인덱스 추가
                    # ---- 디버깅 로그 추가 시작 ----
                    if item_idx < 3: # 처음 3개 항목에 대해서만 키 출력 (로그 과다 방지)
                        print(f"Debug: Article item keys (keyword: {keyword}, index: {item_idx}): {list(item.keys())}")
                        raw_date_val = item.get("date")
                        raw_published_at_val = item.get("publishedAt")
                        print(f"Debug: Raw 'date' value (keyword: {keyword}, index: {item_idx}): '{raw_date_val}' (type: {type(raw_date_val)})")
                        print(f"Debug: Raw 'publishedAt' value (keyword: {keyword}, index: {item_idx}): '{raw_published_at_val}' (type: {type(raw_published_at_val)})")
                    # ---- 디버깅 로그 추가 끝 ----
                    
                    article = {
                        "title": item.get("title", "제목 없음"),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", "내용 없음"),
                        "source": item.get("source", "출처 없음"),  # Serper API 응답에 'source' 필드가 있다고 가정
                        "date": item.get("date") or item.get("publishedAt") or "날짜 없음" # Try "date", then "publishedAt", then default
                    }
                    articles_for_keyword.append(article)
            
            num_found = len(articles_for_keyword)
            keyword_article_counts[keyword] = num_found
            print(f"Found {num_found} articles for keyword: '{keyword}'")
            all_collected_articles.extend(articles_for_keyword)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching articles for keyword '{keyword}' from Serper.dev: {e}")
            # Continue to next keyword if one fails
        except json.JSONDecodeError:
            print(f"Error decoding JSON response for keyword '{keyword}' from Serper.dev. Response: {response.text}")
            # Continue to next keyword

    print("\nSummary of articles collected per keyword:")
    for kw, count in keyword_article_counts.items():
        print(f"- '{kw}': {count} articles")
    print(f"Total articles collected: {len(all_collected_articles)}\n")
            
    return all_collected_articles

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
        os.makedirs(output_dir, exist=True)
        
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
        raise ToolException(f"Error saving newsletter locally: {e}")

import re

def clean_html_markers(html_content: str) -> str:
    """
    Removes ```html and ``` markers and filepath comments from the beginning and end of an HTML string.
    """
    content = html_content

    # 1. 파일 경로 주석 제거 (존재하는 경우)
    # 패턴: 문자열 시작의 공백 + "<!-- filepath: 내용 -->" + 뒤따르는 공백(개행 포함)
    comment_pattern = r"^\s*<!--\s*filepath:.*?-->\s*"
    match_comment = re.match(comment_pattern, content, flags=re.IGNORECASE | re.DOTALL)
    if match_comment:
        # 주석 및 주석 뒤 공백 이후의 문자열을 가져옴
        content = content[match_comment.end():]

    # 2. HTML 시작 마커 제거 (존재하는 경우)
    # 패턴: (새로운) 문자열 시작의 공백 + "```html" + 뒤따르는 공백(개행 포함)
    html_marker_pattern = r"^\s*```html\s*"
    match_html_marker = re.match(html_marker_pattern, content) # ```html은 대소문자 구분 없음 불필요
    if match_html_marker:
        # HTML 마커 및 마커 뒤 공백 이후의 문자열을 가져옴
        content = content[match_html_marker.end():]

    # 3. 끝부분 ``` 마커 제거
    content = content.rstrip()  # 먼저 오른쪽 끝 공백 제거
    if content.endswith("```"):
        content = content[:-len("```")]
    
    # 최종적으로 앞뒤 공백 제거
    return content.strip()

def generate_keywords_with_gemini(domain: str, count: int = 10) -> list[str]:
    """
    Generates trend keywords for a given domain using Google Gemini.
    """
    if not config.GEMINI_API_KEY: # GOOGLE_API_KEY 대신 GEMINI_API_KEY 사용
        console.print("[bold red]Error: GEMINI_API_KEY is not configured. Cannot generate keywords.[/bold red]")
        return []

    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro-exp-03-25", google_api_key=config.GEMINI_API_KEY, temperature=0.7) # 모델명 변경

        prompt_template = PromptTemplate.from_template(
            "Please generate exactly {count} of the latest trend keywords related to the field of '{domain}'. Present each keyword on a new line without any numbering or bullet points."
        )
        
        chain = prompt_template | llm | StrOutputParser()
        
        console.print(f"\n[cyan]Generating keywords for '{domain}' using Google Gemini...[/cyan]")
        console.print(f"[cyan]Prompt sent to Gemini:[/cyan] {prompt_template.format(domain=domain, count=count)}")
        
        response_content = chain.invoke({"domain": domain, "count": count})
        
        console.print(f"\n[cyan]Raw response from Gemini:[/cyan]\n{response_content}")
        
        # Process the response: split by newlines and remove empty strings
        keywords = [keyword.strip() for keyword in response_content.split('\n') if keyword.strip()]
        
        # Ensure we return the requested number of keywords, even if Gemini provides more or less
        final_keywords = keywords[:count]
        if len(final_keywords) < count and keywords: # If not enough, try to take from the beginning
             final_keywords = keywords 
        
        # If Gemini returns a single line with comma separation (less ideal but handle it)
        if len(final_keywords) == 1 and ',' in final_keywords[0]:
            final_keywords = [kw.strip() for kw in final_keywords[0].split(',')][:count]


        console.print(f"\n[cyan]Processed keywords (target: {count}):[/cyan]\n{final_keywords}")
        
        if not final_keywords:
            console.print("[yellow]Warning: Gemini did not return any keywords or the format was unexpected.[/yellow]")
            return []
            
        return final_keywords

    except Exception as e:
        console.print(f"[bold red]Error generating keywords with Gemini: {e}[/bold red]")
        return []
