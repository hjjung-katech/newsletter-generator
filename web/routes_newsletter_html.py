"""Route registration for newsletter HTML retrieval endpoint."""

import json
import sqlite3

from flask import Flask
from flask.typing import ResponseReturnValue


def register_newsletter_html_route(app: Flask, database_path: str) -> None:
    """Register newsletter HTML route on the given Flask app."""

    @app.route("/api/newsletter-html/<job_id>")  # type: ignore[untyped-decorator]
    def get_newsletter_html(job_id: str) -> ResponseReturnValue:
        """작업 ID에 해당하는 뉴스레터 HTML을 직접 반환"""
        try:
            conn = sqlite3.connect(database_path)
            cursor = conn.cursor()
            cursor.execute("SELECT status, result FROM history WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                return (
                    "<html><body><h1>뉴스레터를 찾을 수 없습니다</h1></body></html>",
                    404,
                )

            status, result_json = row
            if status != "completed":
                return (
                    "<html><body><h1>뉴스레터 생성이 완료되지 않았습니다</h1></body></html>",
                    400,
                )

            result = json.loads(result_json) if result_json else {}
            html_content = result.get("html_content", "")

            if not html_content:
                return (
                    "<html><body><h1>뉴스레터 콘텐츠가 없습니다</h1></body></html>",
                    404,
                )

            # HTML 콘텐츠를 직접 반환 (UTF-8 인코딩 명시)
            return html_content, 200, {"Content-Type": "text/html; charset=utf-8"}

        except Exception as e:
            error_html = f"""
            <html>
            <head><meta charset="utf-8"></head>
            <body>
                <h1>오류 발생</h1>
                <p>뉴스레터를 불러오는 중 오류가 발생했습니다: {str(e)}</p>
            </body>
            </html>
            """
            return error_html, 500, {"Content-Type": "text/html; charset=utf-8"}
