from flask import Blueprint, current_app, jsonify, request

from newsletter_core.public.generation import suggest_keywords

bp = Blueprint("suggest", __name__, url_prefix="/api")


@bp.post("/suggest")
def suggest():
    """키워드 추천 API 엔드포인트"""
    data = request.get_json(force=True)
    domain = (data.get("domain") or "").strip()
    if not domain:
        return jsonify({"error": "domain required"}), 400
    try:
        keywords = suggest_keywords(domain, count=10)
        return jsonify({"keywords": keywords})
    except Exception as exc:
        current_app.logger.exception("suggest failed")
        return jsonify({"error": str(exc)}), 500
