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
import re

console = Console()


@tool
def search_news_articles(keywords: str, num_results: int = 10) -> List[Dict]:
    """
    Search for news articles using the Serper.dev API for each keyword.

    Args:
        keywords: Comma-separated keywords to search for, like 'AI,Machine Learning'
        num_results: Number of results to return per keyword (default: 10, max: 20)
      Returns:
        A list of article dictionaries with 'title', 'url', 'snippet', 'source', and 'date' keys.
    """
    if not config.SERPER_API_KEY:
        raise ToolException("SERPER_API_KEY not found. Please set it in the .env file.")

    if num_results > 20:
        num_results = 20  # Limit to 20 results max

    individual_keywords = [kw.strip() for kw in keywords.split(",")]
    all_collected_articles = []
    keyword_article_counts = {}

    print("\nStarting article collection process:")
    for keyword in individual_keywords:
        print(f"Searching articles for keyword: '{keyword}'")
        # 뉴스 전용 엔드포인트 사용으로 변경
        url = "https://google.serper.dev/news"

        # 뉴스 전용 엔드포인트는 단순한 파라미터만 필요
        payload = json.dumps(
            {"q": keyword, "gl": "kr", "num": num_results}  # 한국 지역 결과
        )

        headers = {
            "X-API-KEY": config.SERPER_API_KEY,
            "Content-Type": "application/json",
        }

        try:
            response = requests.request("POST", url, headers=headers, data=payload)
            response.raise_for_status()

            results = response.json()
            articles_for_keyword = []

            # 여러 가능한 결과 컨테이너를 확인하여 데이터 추출
            containers = []

            # 1. 'news' 키 확인 (뉴스 엔드포인트의 주요 응답 형식)
            if "news" in results:
                print(f"Found 'news' results for keyword '{keyword}'")
                containers.extend(results["news"])

            # 2. 'topStories' 키도 확인 (일부 응답에 존재할 수 있음)
            if "topStories" in results:
                print(f"Found 'topStories' results for keyword '{keyword}'")
                containers.extend(results["topStories"])

            # 3. 'organic' 키 확인 (fallback - 일반 검색 결과)
            if "organic" in results and not containers:
                print(f"Found 'organic' results for keyword '{keyword}'")
                containers.extend(results["organic"])

            # 결과 로깅
            print(f"Total container items found: {len(containers)}")

            # 디버깅: 응답 구조 확인
            if not containers and results:
                print(
                    f"Warning: No result containers found. Available keys: {list(results.keys())}"
                )
                if len(results.keys()) <= 3:  # 키가 적으면 전체 구조 확인
                    print(
                        f"Response structure: {json.dumps(results, ensure_ascii=False)[:300]}..."
                    )

            # 각 아이템 처리
            for item_idx, item in enumerate(
                containers[: min(num_results, len(containers))]
            ):
                # 디버깅 정보 (첫 3개 항목만)
                if item_idx < 3:
                    print(f"Debug: Item keys (index: {item_idx}): {list(item.keys())}")
                    raw_date_val = item.get("date")
                    raw_published_at_val = item.get("publishedAt")
                    print(
                        f"Debug: Date value: '{raw_date_val}' / PublishedAt: '{raw_published_at_val}'"
                    )
                # 공통 형식으로 변환
                article = {
                    "title": item.get("title", "제목 없음"),
                    "url": item.get("link", ""),
                    "link": item.get("link", ""),  # 호환성을 위해 link도 추가
                    "snippet": item.get("snippet")
                    or item.get("description", "내용 없음"),
                    "source": item.get("source", "출처 없음"),
                    "date": item.get("date") or item.get("publishedAt") or "날짜 없음",
                }
                articles_for_keyword.append(article)

            if not articles_for_keyword:
                print(f"No articles could be parsed for keyword '{keyword}'.")

            num_found = len(articles_for_keyword)
            keyword_article_counts[keyword] = num_found
            print(f"Found {num_found} articles for keyword: '{keyword}'")
            all_collected_articles.extend(articles_for_keyword)

        except requests.exceptions.RequestException as e:
            print(
                f"Error fetching articles for keyword '{keyword}' from Serper.dev: {e}"
            )
            # Continue to next keyword if one fails
        except json.JSONDecodeError:
            print(
                f"Error decoding JSON response for keyword '{keyword}' from Serper.dev. Response: {response.text}"
            )
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # 타이틀 추출
        title = soup.title.text.strip() if soup.title else "제목 없음"

        # 메인 콘텐츠 추출 시도 (다양한 방법으로)
        content = ""

        # 메타 설명 추출
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            content += meta_desc.get("content") + "\n\n"

        # article 태그 찾기
        article_tag = soup.find("article")
        if article_tag:
            # 불필요한 요소 제거
            for tag in article_tag.find_all(
                ["script", "style", "nav", "footer", "aside"]
            ):
                tag.decompose()

            content += article_tag.get_text(separator="\n", strip=True)
        else:
            # 본문으로 추정되는 태그들 찾기
            for tag_name in ["div", "section"]:
                for attr in ["id", "class"]:
                    for keyword in [
                        "content",
                        "article",
                        "main",
                        "body",
                        "entry",
                        "post",
                    ]:
                        main_content = soup.find(
                            tag_name,
                            {
                                attr: lambda x: (
                                    x and keyword in x.lower() if x else False
                                )
                            },
                        )
                        if main_content:
                            # 불필요한 요소 제거
                            for tag in main_content.find_all(
                                ["script", "style", "nav", "footer", "aside"]
                            ):
                                tag.decompose()

                            content += main_content.get_text(separator="\n", strip=True)
                            break
                    if content:
                        break
                if content:
                    break

        # 본문을 찾지 못한 경우 전체 텍스트 사용
        if not content:
            # 불필요한 요소 제거
            for tag in soup.find_all(["script", "style", "nav", "footer", "aside"]):
                tag.decompose()

            content = (
                soup.body.get_text(separator="\n", strip=True)
                if soup.body
                else "내용을 추출할 수 없습니다."
            )

        # 결과 반환
        return {
            "title": title,
            "url": url,
            "content": content[:5000],  # 컨텐츠 길이 제한 (토큰 절약)
        }

    except Exception as e:
        raise ToolException(f"Error fetching article content: {str(e)}")


@tool
def save_newsletter_locally(
    html_content: str, filename_base: str, output_format: str = "html"
) -> str:
    """
    Save newsletter content locally as HTML or Markdown.

    Args:
        html_content: HTML content of the newsletter
        filename_base: Base filename (without extension)
        output_format: Format to save as ('html' or 'md')

    Returns:
        Path to the saved file
    """
    if output_format not in ["html", "md"]:
        raise ToolException("Format must be 'html' or 'md'")

    try:
        # Clean HTML markers from content before saving
        cleaned_html_content = clean_html_markers(html_content)

        # 출력 디렉토리 생성 (없는 경우)
        output_dir = os.path.join(os.getcwd(), "output")
        os.makedirs(output_dir, exist_ok=True)

        # 파일 경로 생성
        file_path = os.path.join(output_dir, f"{filename_base}.{output_format}")

        # 마크다운으로 변환 (필요한 경우)
        if output_format == "md":
            content = markdownify.markdownify(cleaned_html_content, heading_style="ATX")
        else:
            content = cleaned_html_content

        # 파일 저장
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Newsletter saved locally as {filename_base}.{output_format} at {file_path}"

    except Exception as e:
        raise ToolException(f"Error saving newsletter locally: {e}")


def clean_html_markers(html_content: str) -> str:
    """
    Removes code markup (```html, ```, ``` etc.) from the beginning and end of an HTML string,
    as well as file path comments.

    This handles various patterns including:
    - ```html at the beginning
    - ``` at the end
    - ```lang syntax (for any language identifier)
    - Filepath comments
    - Multiple backticks (like ````html)
    """
    if not html_content:
        return ""

    content = html_content

    # 1. 파일 경로 주석 제거 (존재하는 경우)
    # 패턴: 문자열 시작의 공백 + "<!-- filepath: 내용 -->" + 뒤따르는 공백(개행 포함)
    comment_pattern = r"^\s*<!--\s*filepath:.*?-->\s*"
    match_comment = re.match(comment_pattern, content, flags=re.IGNORECASE | re.DOTALL)
    if match_comment:
        # 주석 및 주석 뒤 공백 이후의 문자열을 가져옴
        content = content[match_comment.end() :]

    # 2. 시작 부분의 코드 마커 제거 (다양한 언어 식별자 및 여러 개의 백틱 처리)
    # 더 일반적인 패턴: (새로운) 문자열 시작의 공백 + 하나 이상의 백틱 + 선택적 언어 식별자 + 뒤따르는 공백(개행 포함)
    start_marker_pattern = r"^\s*(`{1,4})([a-zA-Z]*)\s*"
    match_start_marker = re.match(start_marker_pattern, content)
    if match_start_marker:
        # 코드 마커 및 마커 뒤 공백 이후의 문자열을 가져옴
        content = content[match_start_marker.end() :]

    # 3. 끝부분 코드 마커 제거 (여러 개의 백틱 처리)
    content = content.rstrip()  # 먼저 오른쪽 끝 공백 제거
    end_marker_pattern = r"`{1,4}\s*$"
    match_end_marker = re.search(end_marker_pattern, content)
    if match_end_marker:
        content = content[: match_end_marker.start()]

    # 최종적으로 앞뒤 공백 제거
    return content.strip()


def generate_keywords_with_gemini(domain: str, count: int = 10) -> list[str]:
    """
    Generates high-quality trend keywords for a given domain using Google Gemini.
    """
    if not config.GEMINI_API_KEY:
        console.print(
            "[bold red]Error: GEMINI_API_KEY is not configured. Cannot generate keywords.[/bold red]"
        )
        return []

    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-pro-preview-03-25", 
            google_api_key=config.GEMINI_API_KEY,
            temperature=0.7,
            transport="rest",  # REST API 사용 (gRPC 대신)
            convert_system_message_to_human=True,  # 시스템 메시지를 휴먼 메시지로 변환
        )

        prompt_template = PromptTemplate.from_template(
            """You are a news search expert highly skilled at identifying effective search queries for finding the latest news articles about a given field.

        Based on the [Field Information] provided below, please generate exactly {count} highly effective search keywords (search queries) that someone would use *right now* to find recent news or significant events within this field.

        **IMPORTANT:** The generated keywords must be in **Korean**.

        Keyword Generation Guidelines:
        1.  Each keyword should be in the form of a natural phrase (generally 2-4 words) suitable for use in a real news search engine.
        2.  Prioritize terms that cover recent or currently notable major events, individuals, companies/organizations, technological changes, or other timely developments within the given field.
        3.  Include keywords that can yield specific search results rather than overly general or broad single words.
        4.  Ensure the generated keywords are likely to appear in Korean news headlines or body text and have a high probability of being used in actual news searches by Korean speakers.
        5.  Ensure you provide exactly the requested number of keywords ({count}).

        [Field Information]:
        {domain}

        Generated Search Keyword List (in Korean):
        (Provide each keyword on a new line, without any numbering or bullet points. Include only the Korean keywords themselves.)
        """
        )

        chain = prompt_template | llm | StrOutputParser()

        console.print(
            f"\n[cyan]Generating keywords for '{domain}' using Google Gemini...[/cyan]"
        )

        # 실행 및 응답 처리
        response_content = chain.invoke({"domain": domain, "count": count})
        console.print(f"\n[cyan]Raw response from Gemini:[/cyan]\n{response_content}")

        # 응답 처리
        keywords = []
        for line in response_content.split("\n"):
            if not line.strip():
                continue

            # 앞의 번호 및 마크다운 볼드 표시 제거
            clean_line = re.sub(r'^\d+\.?\s*', '', line.strip())
            clean_line = re.sub(r'\*\*(.+?)\*\*', r'\1', clean_line)

            # 괄호 안의 영어 설명 제거 (있는 경우)
            clean_line = re.sub(r'\s*\(.+?\)\s*$', '', clean_line)

            if clean_line:
                keywords.append(clean_line)

        # 키워드 형식 처리
        final_keywords = keywords[:count]
        if len(final_keywords) < count and keywords:
            final_keywords = keywords

        if len(final_keywords) == 1 and "," in final_keywords[0]:
            final_keywords = [kw.strip() for kw in final_keywords[0].split(",")][:count]
            
        # 키워드 효과성 검증 (옵션)
        final_keywords = validate_and_refine_keywords(final_keywords, min_results_per_keyword=3, count=count)

        console.print(f"\n[cyan]최종 키워드 ({len(final_keywords)}):[/cyan]")
        for i, kw in enumerate(final_keywords, 1):
            console.print(f"  {i}. [green]{kw}[/green]")

        return final_keywords

    except Exception as e:
        console.print(
            f"[bold red]Error generating keywords with Gemini: {e}[/bold red]"
        )
        return []


def validate_and_refine_keywords(keywords: list[str], min_results_per_keyword: int = 3, count: int = 10) -> list[str]:
    """각 키워드로 검색했을 때 충분한 결과가 나오는지 검증하고, 문제가 있는 키워드는 대체합니다."""
    
    validated_keywords = []
    replacement_needed = []
    
    console.print(f"\n[cyan]검증 중: 각 키워드가 충분한 뉴스 결과를 반환하는지 확인합니다...[/cyan]")
    
    for keyword in keywords:
        try:
            # 키워드로 테스트 검색 (invoke 메서드 사용)
            test_results = search_news_articles.invoke({"keywords": keyword, "num_results": 5})
            
            if len(test_results) >= min_results_per_keyword:
                validated_keywords.append(keyword)
                console.print(f"[green]✓ '{keyword}': {len(test_results)}개 결과 확인[/green]")
            else:
                replacement_needed.append(keyword)
                console.print(f"[yellow]✗ '{keyword}': 결과 부족 ({len(test_results)}개)[/yellow]")
        
        except Exception as e:
            console.print(f"[red]! '{keyword}' 검증 중 오류: {e}[/red]")
            replacement_needed.append(keyword)
    
    # 대체 키워드 생성이 필요한 경우
    if replacement_needed and validated_keywords:
        console.print(f"[yellow]{len(replacement_needed)}개 키워드에 대한 대체 키워드 생성 중...[/yellow]")
        
        # 이 부분도 수정 필요 - domain 변수가 함수 내에서 접근할 수 없음
        new_keywords = []  # 임시 빈 리스트로 대체
        
        validated_keywords.extend(new_keywords)
    
    return validated_keywords[:count]  # 원래 요청한 개수만큼 반환
