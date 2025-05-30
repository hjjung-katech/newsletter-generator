import json
import os

from .utils.logger import get_logger

# 로거 초기화
logger = get_logger()


class TemplateManager:
    """템플릿 설정 관리를 담당하는 클래스"""

    _instance = None
    _config = None

    @classmethod
    def get_instance(cls):
        """싱글톤 패턴으로 인스턴스 반환"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """설정 파일 로드"""
        self.load_config()

    def load_config(self, config_path=None):
        """지정된 경로 또는 기본 경로에서 설정 파일 로드"""
        if config_path is None:
            # 기본 경로 설정
            config_path = os.path.join(os.getcwd(), "config", "template_config.json")

        # 디렉토리 확인 및 생성
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        # 파일 존재 확인
        if not os.path.exists(config_path):
            # 기본 설정 생성
            self._config = self._default_config()
            # 파일 저장
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
            print(f"기본 설정 파일 생성됨: {config_path}")
        else:
            # 기존 설정 로드
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
                logger.info(f"설정 파일 로드됨: {config_path}")
            except Exception as e:
                logger.error(f"설정 파일 로드 실패: {e}")
                self._config = self._default_config()

    def _default_config(self):
        """기본 설정 제공"""
        return {
            "company": {
                "name": "산업통상자원 R&D 전략기획단",
                "copyright_year": "2025",
                "tagline": "최신 기술 동향을 한눈에",
            },
            "editor": {
                "name": "Google Gemini",
                "title": "편집자",
                "email": "hjjung2@osp.re.kr",
                "signature": "OSP 뉴스레터 편집팀 드림",
            },
            "footer": {
                "disclaimer": "이 뉴스레터는 정보 제공을 목적으로 하며, 내용의 정확성을 보장하지 않습니다.",
                "contact_info": "문의사항: hjjung2@osp.re.kr",
            },
            "header": {
                "title_prefix": "주간 산업 동향 뉴스 클리핑",
                "greeting_prefix": "안녕하십니까, ",
            },
            "audience": {
                "description": "전문위원 여러분",
                "organization": "전략프로젝트팀",
            },
            "style": {
                "primary_color": "#3498db",
                "secondary_color": "#2c3e50",
                "font_family": "Malgun Gothic, sans-serif",
            },
        }

    def get(self, path, default=None):
        """경로로 설정값 가져오기 (점 표기법)"""
        if not self._config:
            return default

        parts = path.split(".")
        current = self._config

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default

        return current

    def set_config(self, config):
        """테스트용: 설정을 직접 설정"""
        self._config = config
