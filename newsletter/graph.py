"""
Newsletter Generator - LangGraph Workflow
이 모듈은 LangGraph를 사용하여 뉴스레터 생성 워크플로우를 정의합니다.
"""

from typing import Dict, List, Any, Tuple, TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.messages import HumanMessage
import json

# State 정의
class NewsletterState(TypedDict):
    """뉴스레터 생성 과정의 상태를 정의하는 클래스"""
    # 입력 값
    keywords: List[str]
    # 중간 결과물
    collected_articles: List[Dict]
    article_summaries: Dict
    # 최종 결과물
    newsletter_html: str
    # 제어 및 메타데이터
    error: str
    status: str  # 'collecting', 'summarizing', 'composing', 'complete', 'error'

# 노드 함수 정의
def collect_articles(state: NewsletterState) -> NewsletterState:
    """
    키워드를 기반으로 기사를 수집하는 노드
    """
    from .tools import search_news_articles
    
    try:
        # 키워드 문자열 생성
        keyword_str = ", ".join(state["keywords"])
        
        # 기사 수집
        articles = search_news_articles(keywords=keyword_str, num_results=10)
        
        # 상태 업데이트
        return {
            **state,
            "collected_articles": articles,
            "status": "summarizing"
        }
    except Exception as e:
        return {
            **state,
            "error": f"기사 수집 중 오류 발생: {str(e)}",
            "status": "error"
        }

def summarize_articles(state: NewsletterState) -> NewsletterState:
    """
    수집된 기사를 요약하는 노드
    """
    from .chains import get_summarization_chain
    
    try:
        # 기사가 없는 경우
        if not state["collected_articles"]:
            return {
                **state,
                "error": "수집된 기사가 없습니다.",
                "status": "error"
            }
        
        # 요약 체인 가져오기
        summarization_chain = get_summarization_chain()
        
        # 체인 실행
        keyword_str = ", ".join(state["keywords"])
        chain_input = {
            "keywords": keyword_str,
            "articles": state["collected_articles"]
        }
        
        result = summarization_chain.invoke(chain_input)
        
        # 상태 업데이트
        return {
            **state,
            "newsletter_html": result,
            "status": "complete"
        }
    except Exception as e:
        return {
            **state,
            "error": f"기사 요약 중 오류 발생: {str(e)}",
            "status": "error"
        }

def handle_error(state: NewsletterState) -> Literal["end"]:
    """
    에러 처리 노드
    """
    print(f"[오류] {state['error']}")
    return "end"

# 그래프 정의
def create_newsletter_graph() -> StateGraph:
    """
    뉴스레터 생성을 위한 LangGraph 워크플로우 그래프 생성
    """
    workflow = StateGraph(NewsletterState)
    
    # 노드 추가
    workflow.add_node("collect_articles", collect_articles)
    workflow.add_node("summarize_articles", summarize_articles)
    workflow.add_node("handle_error", handle_error)
    
    # 엣지 추가 (노드 간 전환)
    workflow.add_edge("collect_articles", "summarize_articles")
    workflow.add_conditional_edges(
        "collect_articles",
        lambda state: "handle_error" if state["status"] == "error" else "summarize_articles"
    )
    workflow.add_conditional_edges(
        "summarize_articles",
        lambda state: "handle_error" if state["status"] == "error" else END
    )
    workflow.add_edge("handle_error", END)
    
    # 시작 노드 설정
    workflow.set_entry_point("collect_articles")
    
    return workflow.compile()

# 뉴스레터 생성 함수
def generate_newsletter(keywords: List[str]) -> Tuple[str, str]:
    """
    키워드를 기반으로 뉴스레터를 생성하는 메인 함수
    
    Args:
        keywords: 키워드 리스트
        
    Returns:
        (뉴스레터 HTML, 상태)
    """
    # 초기 상태 생성
    initial_state = {
        "keywords": keywords,
        "collected_articles": [],
        "article_summaries": {},
        "newsletter_html": "",
        "error": "",
        "status": "collecting"
    }
    
    # 그래프 생성 및 실행
    graph = create_newsletter_graph()
    final_state = graph.invoke(initial_state)
    
    # 결과 반환
    if final_state["status"] == "complete":
        return final_state["newsletter_html"], "success"
    else:
        return final_state["error"], "error"
