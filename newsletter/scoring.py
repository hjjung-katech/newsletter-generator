"""Scoring utilities for ranking news articles."""

from __future__ import annotations

import json
import logging
import math
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage

from . import config
from .chains import get_llm
from .date_utils import parse_date_string
from .utils.error_handling import handle_exception
from .utils.logger import get_logger

# Default weights for priority score calculation
DEFAULT_WEIGHTS = {
    "relevance": 0.40,
    "impact": 0.25,
    "novelty": 0.15,
    "source_tier": 0.10,
    "recency": 0.10,
}

# 로거 초기화
logger = get_logger()


def load_scoring_weights_from_config(
    config_file: str = "config.yml",
) -> Dict[str, float]:
    """Load scoring weights from config.yml file.

    Args:
        config_file: Path to config file (kept for compatibility)

    Returns:
        Dict[str, float]: Scoring weights dictionary
    """
    # 1순위: config_manager 사용 (권장)
    try:
        from .config_manager import config_manager

        weights = config_manager.get_scoring_weights()
        logger.info("✅ 스코어링 가중치를 config_manager에서 로드했습니다.")
        return weights
    except ImportError:
        logger.warning("config_manager를 가져올 수 없습니다. fallback 모드로 전환합니다.")
    except Exception as e:
        logger.warning(f"config_manager에서 가중치 로드 실패: {e}. fallback 모드로 전환합니다.")

    # 2순위: 직접 yaml 파일 읽기 (fallback)
    fallback_weights = {
        "relevance": 0.35,
        "impact": 0.25,
        "novelty": 0.15,
        "source_tier": 0.15,
        "recency": 0.10,
    }

    try:
        import sys

        import yaml

        # PyInstaller 환경에서의 경로 처리
        if getattr(sys, "frozen", False):
            # PyInstaller로 빌드된 경우
            base_path = sys._MEIPASS
            config_path = os.path.join(base_path, config_file)
        else:
            # 일반 Python 환경
            config_path = config_file

        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            scoring_config = config_data.get("scoring", {})
            if scoring_config:
                # Validate that all required keys exist and are numeric
                required_keys = set(fallback_weights.keys())
                config_keys = set(scoring_config.keys())

                if required_keys.issubset(config_keys):
                    # Ensure all values are numeric and sum to 1.0 (approximately)
                    weights = {k: float(scoring_config[k]) for k in required_keys}
                    total = sum(weights.values())

                    if abs(total - 1.0) < 0.01:  # Allow small floating point errors
                        logger.info(f"✅ 스코어링 가중치를 {config_file}에서 로드했습니다.")
                        return weights
                    else:
                        logger.warning(
                            f"스코어링 가중치의 합이 {total:.3f}이며 1.0이 아닙니다. 기본값을 사용합니다."
                        )
                else:
                    missing_keys = required_keys - config_keys
                    logger.warning(f"스코어링 가중치 키가 누락되었습니다: {missing_keys}. 기본값을 사용합니다.")
    except Exception as e:
        logger.warning(f"스코어링 가중치를 {config_file}에서 로드할 수 없습니다: {e}. 기본값을 사용합니다.")

    logger.info("⚠️  기본 스코어링 가중치를 사용합니다.")
    return fallback_weights


SCORE_PROMPT = """
You are a professional news editor. Evaluate the article below for the newsletter topic <DOMAIN>.
Return scores only as JSON in the format {{"relevance":1-5,"impact":1-5,"novelty":1-5}}.

Title: {title}
Summary: {summary}
"""


def _get_source_tier(source: str) -> float:
    """Get source tier score and tier name for display."""
    if any(s.lower() in source.lower() for s in config.MAJOR_NEWS_SOURCES["tier1"]):
        return 1.0
    if any(s.lower() in source.lower() for s in config.MAJOR_NEWS_SOURCES["tier2"]):
        return 0.6  # 0.8 → 0.6으로 차이 확대
    return 0.3  # 0.6 → 0.3으로 차이 확대


def _get_source_tier_info(source: str) -> tuple[float, str]:
    """Get source tier score and tier name for display."""
    if any(s.lower() in source.lower() for s in config.MAJOR_NEWS_SOURCES["tier1"]):
        return 1.0, "Tier 1 (주요 언론사)"
    if any(s.lower() in source.lower() for s in config.MAJOR_NEWS_SOURCES["tier2"]):
        return 0.6, "Tier 2 (보조 언론사)"
    return 0.3, "Tier 3 (기타 소스)"


def _get_recency(date_str: Any) -> float:
    dt = parse_date_string(date_str)
    if not dt:
        return 0.0
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        dt = dt.replace(tzinfo=timezone.utc)
    days = (now - dt).total_seconds() / 86400
    return math.exp(-days / 14)


def _parse_llm_json(text: str) -> Dict[str, float]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception as e:
            handle_exception(e, "점수 JSON 파싱", log_level=logging.INFO)
            return {"relevance": 1, "impact": 1, "novelty": 1}
    return {"relevance": 1, "impact": 1, "novelty": 1}


def _is_nested_connection_error(exception) -> bool:
    """
    중첩된 예외 구조에서 연결 오류를 감지합니다.
    예: ('Connection aborted.', ConnectionResetError(...))
    """
    import socket

    # Direct instance check
    if isinstance(exception, (ConnectionResetError, ConnectionError, socket.error)):
        return True

    # Check for nested tuple exceptions (like requests library wraps)
    if isinstance(exception, tuple) and len(exception) > 1:
        for item in exception:
            if isinstance(item, (ConnectionResetError, ConnectionError, socket.error)):
                return True

    # Check exception args for nested exceptions
    if hasattr(exception, "args") and exception.args:
        for arg in exception.args:
            if isinstance(arg, (ConnectionResetError, ConnectionError, socket.error)):
                return True
            # Check nested tuples in args
            if isinstance(arg, tuple):
                for nested_item in arg:
                    if isinstance(
                        nested_item,
                        (ConnectionResetError, ConnectionError, socket.error),
                    ):
                        return True

    # String-based detection as fallback
    error_str = str(exception).lower()
    connection_keywords = [
        "연결",
        "강제",
        "끊",
        "reset",
        "connection",
        "timeout",
        "network",
        "10054",
        "10061",
        "10060",
        "connection aborted",
        "connection reset",
        "현재 연결은",
        "원격 호스트",
        "강제로 끊",
    ]

    return any(keyword in error_str for keyword in connection_keywords)


def request_llm_scores(
    article: Dict[str, Any], domain: str, llm=None
) -> Dict[str, float]:
    import time

    if llm is None:
        llm = get_llm(temperature=0)

    # domain이 None이거나 비어있을 때 기본값 사용
    if not domain:
        domain = "기술 및 산업 동향"

    prompt = SCORE_PROMPT.replace("<DOMAIN>", domain).format(
        title=article.get("title", ""),
        summary=article.get("content") or article.get("snippet", ""),
    )
    message = HumanMessage(content=prompt)

    # Enhanced retry logic for connection errors during scoring
    max_retries = 3
    base_delay = 2

    for attempt in range(max_retries + 1):
        try:
            result = llm.invoke([message])
            if isinstance(result, AIMessage):
                text = result.content
            else:
                text = str(result)
            return _parse_llm_json(text)

        except Exception as e:
            # Enhanced connection error detection
            is_connection_error = _is_nested_connection_error(e)

            if is_connection_error:
                if attempt < max_retries:
                    delay = base_delay * (2**attempt)  # Exponential backoff
                    logger.warning(
                        f"스코어링 연결 오류 (시도 {attempt + 1}/{max_retries + 1}), {delay}초 후 재시도: {e}"
                    )
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"스코어링 최종 실패, 기본 점수 사용: {e}")
                    return {"relevance": 3, "impact": 3, "novelty": 3}  # Default scores
            else:
                # Non-connection errors - log and return defaults immediately
                logger.error(f"스코어링 오류 (재시도 불가), 기본 점수 사용: {e}")
                return {"relevance": 3, "impact": 3, "novelty": 3}

    # Should not reach here, but fallback
    return {"relevance": 3, "impact": 3, "novelty": 3}


def calculate_priority_score(
    article: Dict[str, Any],
    domain: str,
    weights: Optional[Dict[str, float]] = None,
    llm=None,
) -> float:
    """Calculate a weighted priority score for a single article.

    This also stores the raw LLM evaluation metrics under ``article["scoring"]``
    so that reweighting can be performed without another LLM call.
    """

    if weights is None:
        weights = load_scoring_weights_from_config()

    scores = request_llm_scores(article, domain, llm=llm)
    # Save raw scores for later reuse
    article["scoring"] = scores

    relevance = scores.get("relevance", 1) / 5
    impact = scores.get("impact", 1) / 5
    novelty = scores.get("novelty", 1) / 5

    # Source tier 정보 저장
    source_tier_score, source_tier_name = _get_source_tier_info(
        article.get("source", "")
    )
    article["source_tier_score"] = source_tier_score
    article["source_tier_name"] = source_tier_name

    recency = _get_recency(article.get("date"))

    priority = (
        weights["relevance"] * relevance
        + weights["impact"] * impact
        + weights["novelty"] * novelty
        + weights["source_tier"] * source_tier_score
        + weights["recency"] * recency
    ) * 100

    return round(priority, 4)


def score_articles(
    articles: List[Dict[str, Any]],
    domain: str,
    top_n: Optional[int] = 10,
    weights: Optional[Dict[str, float]] = None,
    llm=None,
) -> List[Dict[str, Any]]:
    """Score and rank a list of articles.

    Parameters
    ----------
    articles : list of dict
        Articles to score in-place.
    domain : str
        The newsletter domain/topic.
    top_n : Optional[int]
        Number of top articles to return. ``None`` returns all scored articles.

    Returns
    -------
    list of dict
        The scored (and sorted) articles.
    """

    if weights is None:
        weights = load_scoring_weights_from_config()

    scored_list = []
    for article in articles:
        score = calculate_priority_score(article, domain, weights=weights, llm=llm)
        article["priority_score"] = score
        scored_list.append(article)

    scored_list.sort(key=lambda a: a["priority_score"], reverse=True)

    # Tier별 통계 출력
    tier_stats = {}
    for article in scored_list:
        tier_name = article.get("source_tier_name", "Unknown")
        if tier_name not in tier_stats:
            tier_stats[tier_name] = {"count": 0, "scores": []}
        tier_stats[tier_name]["count"] += 1
        tier_stats[tier_name]["scores"].append(article["priority_score"])

    logger.info("[통계] Source Tier 분포 및 점수 통계:")
    for tier_name, stats in tier_stats.items():
        avg_score = (
            sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0
        )
        logger.info(f"  - {tier_name}: {stats['count']}개 기사, 평균 점수: {avg_score:.1f}")

    if top_n is None:
        return scored_list

    return scored_list[:top_n]
