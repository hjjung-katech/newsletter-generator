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

from newsletter_core.public.settings import get_major_news_sources

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
        return weights  # type: ignore[no-any-return]
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
        import yaml  # type: ignore[import-untyped]

        if os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
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
    if any(s.lower() in source.lower() for s in get_major_news_sources()["tier1"]):
        return 1.0
    if any(s.lower() in source.lower() for s in get_major_news_sources()["tier2"]):
        return 0.6  # 0.8 → 0.6으로 차이 확대
    return 0.3  # 0.6 → 0.3으로 차이 확대


def _get_source_tier_info(source: str) -> tuple[float, str]:
    """Get source tier score and tier name for display."""
    if any(s.lower() in source.lower() for s in get_major_news_sources()["tier1"]):
        return 1.0, "Tier 1 (주요 언론사)"
    if any(s.lower() in source.lower() for s in get_major_news_sources()["tier2"]):
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
            return json.loads(match.group(0))  # type: ignore[no-any-return]
        except Exception as e:
            handle_exception(e, "점수 JSON 파싱", log_level=logging.INFO)
            return {"relevance": 1, "impact": 1, "novelty": 1}
    return {"relevance": 1, "impact": 1, "novelty": 1}


def request_llm_scores(
    article: Dict[str, Any], domain: str, llm: Any = None
) -> Dict[str, float]:
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
    result = llm.invoke([message])
    if isinstance(result, AIMessage):
        text = result.content
    else:
        text = str(result)
    return _parse_llm_json(text)


def calculate_priority_score(
    article: Dict[str, Any],
    domain: str,
    weights: Optional[Dict[str, float]] = None,
    llm: Any = None,
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
    llm: Any = None,
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
    tier_stats: Dict[str, Any] = {}
    for article in scored_list:
        tier_name = article.get("source_tier_name", "Unknown")
        if tier_name not in tier_stats:
            tier_stats[tier_name] = {"count": 0, "scores": []}
        tier_stats[tier_name]["count"] += 1
        tier_stats[tier_name]["scores"].append(article["priority_score"])

    logger.info("📊 Source Tier 분포 및 점수 통계:")
    for tier_name, stats in tier_stats.items():
        avg_score = (
            sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0
        )
        logger.info(f"  • {tier_name}: {stats['count']}개 기사, 평균 점수: {avg_score:.1f}")

    if top_n is None:
        return scored_list

    return scored_list[:top_n]
