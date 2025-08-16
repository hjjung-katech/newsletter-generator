import os

# 웹 서비스 모드 체크 - Flask 앱 중복 실행 방지
if os.environ.get("WEB_SERVICE_MODE") == "1":
    # 웹 서비스에서 호출된 경우 Flask 앱 시작 방지
    os.environ["FLASK_APP"] = "none"
    os.environ["FLASK_ENV"] = "none"

from .cli import app

if __name__ == "__main__":
    app()
