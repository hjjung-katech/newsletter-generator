"""Scoring utilities for ranking news articles."""

from __future__ import annotations

import json
import math
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, AIMessage

from .article_filter import MAJOR_NEWS_SOURCES
from .date_utils import parse_date_string
from .chains import get_llm

# Default weights for priority score calculation
DEFAULT_WEIGHTS = {
    "relevance": 0.40,
    "impact": 0.25,
    "novelty": 0.15,
    "source_tier": 0.10,
    "recency": 0.10,
}

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
    scores: Optional[Dict[str, float]] = None,
) -> float:
    if weights is None:
        weights = DEFAULT_WEIGHTS
    if scores is None:
        scores = request_llm_scores(article, domain, llm=llm)
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
    """Score and rank articles using an LLM.

    If ``top_n`` is ``None`` all scored articles are returned in ranked order.
    """

    if weights is None:
        weights = DEFAULT_WEIGHTS

    scored_list = []
    for article in articles:
        scores = request_llm_scores(article, domain, llm=llm)
        source_tier = _get_source_tier(article.get("source", ""))
        recency = _get_recency(article.get("date"))

        relevance = scores.get("relevance", 1) / 5
        impact = scores.get("impact", 1) / 5
        novelty = scores.get("novelty", 1) / 5
        priority_score = (
            weights["relevance"] * relevance
            + weights["impact"] * impact
            + weights["novelty"] * novelty
            + weights["source_tier"] * source_tier
            + weights["recency"] * recency
        ) * 100
        priority_score = round(priority_score, 4)
        article["scoring"] = {
            "relevance": scores.get("relevance", 1),
            "impact": scores.get("impact", 1),
            "novelty": scores.get("novelty", 1),
            "source_tier": source_tier,
            "recency": recency,
        }
        article["priority_score"] = priority_score
        scored_list.append(article)

    scored_list.sort(key=lambda a: a["priority_score"], reverse=True)

    if top_n is not None:
        return scored_list[:top_n]
    return scored_list
