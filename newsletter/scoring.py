"""Scoring utilities for ranking news articles."""

from __future__ import annotations

import json
import math
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage

from .article_filter import MAJOR_NEWS_SOURCES
from .chains import get_llm
from .date_utils import parse_date_string

# Default weights for priority score calculation
DEFAULT_WEIGHTS = {
    "relevance": 0.40,
    "impact": 0.25,
    "novelty": 0.15,
    "source_tier": 0.10,
    "recency": 0.10,
}


def load_scoring_weights_from_config(
    config_file: str = "config.yml",
) -> Dict[str, float]:
    """Load scoring weights from config.yml file.

    Args:
        config_file: Path to the config file

    Returns:
        Dict containing scoring weights, defaults to DEFAULT_WEIGHTS if file not found or invalid
    """
    try:
        import yaml

        if os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            scoring_config = config_data.get("scoring", {})
            if scoring_config:
                # Validate that all required keys exist and are numeric
                required_keys = set(DEFAULT_WEIGHTS.keys())
                config_keys = set(scoring_config.keys())

                if required_keys.issubset(config_keys):
                    # Ensure all values are numeric and sum to 1.0 (approximately)
                    weights = {k: float(scoring_config[k]) for k in required_keys}
                    total = sum(weights.values())

                    if abs(total - 1.0) < 0.01:  # Allow small floating point errors
                        return weights
                    else:
                        print(
                            f"[yellow]Warning: Scoring weights sum to {total:.3f}, not 1.0. Using defaults.[/yellow]"
                        )
                else:
                    missing_keys = required_keys - config_keys
                    print(
                        f"[yellow]Warning: Missing scoring weight keys: {missing_keys}. Using defaults.[/yellow]"
                    )
    except Exception as e:
        print(
            f"[yellow]Warning: Could not load scoring weights from {config_file}: {e}. Using defaults.[/yellow]"
        )

    return DEFAULT_WEIGHTS


SCORE_PROMPT = """
You are a professional news editor. Evaluate the article below for the newsletter topic <DOMAIN>.
Return scores only as JSON in the format {{"relevance":1-5,"impact":1-5,"novelty":1-5}}.

Title: {title}
Summary: {summary}
"""


def _get_source_tier(source: str) -> float:
    if any(s.lower() in source.lower() for s in MAJOR_NEWS_SOURCES["tier1"]):
        return 1.0
    if any(s.lower() in source.lower() for s in MAJOR_NEWS_SOURCES["tier2"]):
        return 0.8
    return 0.6


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
        except Exception:
            pass
    return {"relevance": 1, "impact": 1, "novelty": 1}


def request_llm_scores(
    article: Dict[str, Any], domain: str, llm=None
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
    llm=None,
) -> float:
    """Calculate a weighted priority score for a single article.

    This also stores the raw LLM evaluation metrics under ``article["scoring"]``
    so that reweighting can be performed without another LLM call.
    """

    if weights is None:
        weights = DEFAULT_WEIGHTS

    scores = request_llm_scores(article, domain, llm=llm)
    # Save raw scores for later reuse
    article["scoring"] = scores

    relevance = scores.get("relevance", 1) / 5
    impact = scores.get("impact", 1) / 5
    novelty = scores.get("novelty", 1) / 5
    source_tier = _get_source_tier(article.get("source", ""))
    recency = _get_recency(article.get("date"))

    priority = (
        weights["relevance"] * relevance
        + weights["impact"] * impact
        + weights["novelty"] * novelty
        + weights["source_tier"] * source_tier
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

    scored_list = []
    for article in articles:
        score = calculate_priority_score(article, domain, weights=weights, llm=llm)
        article["priority_score"] = score
        scored_list.append(article)

    scored_list.sort(key=lambda a: a["priority_score"], reverse=True)

    if top_n is None:
        return scored_list

    return scored_list[:top_n]
