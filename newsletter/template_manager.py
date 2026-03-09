from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, ClassVar

import yaml  # type: ignore[import-untyped]

from .config_manager import get_newsletter_settings
from .utils.logger import get_logger

# 로거 초기화
logger = get_logger()


class TemplateManager:
    """템플릿 설정 관리를 담당하는 클래스"""

    _instance: ClassVar[TemplateManager | None] = None
    _config: dict[str, Any] | None = None

    @classmethod
    def get_instance(cls) -> TemplateManager:
        """싱글톤 패턴으로 인스턴스 반환"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        """설정 파일 로드"""
        self.load_config()

    def load_config(self, config_path: str | Path | None = None) -> None:
        """지정된 경로 또는 canonical runtime 설정에서 템플릿 설정 로드"""
        if config_path is None:
            try:
                self._config = self._build_runtime_config(get_newsletter_settings())
                logger.info("Runtime newsletter settings loaded for template manager")
            except Exception as e:
                logger.error(f"Runtime newsletter settings load failed: {e}")
                self._config = self._default_config()
            return

        path = Path(config_path)
        if not path.exists():
            logger.warning(f"설정 파일이 없어 기본 템플릿 설정을 사용합니다: {path}")
            self._config = self._default_config()
            return

        try:
            self._config = self._load_explicit_config(path)
            logger.info(f"설정 파일 로드됨: {path}")
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            self._config = self._default_config()

    def _default_config(self) -> dict[str, Any]:
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

    def _build_runtime_config(
        self, newsletter_settings: dict[str, Any]
    ) -> dict[str, Any]:
        config = self._default_config()
        mapping = {
            "company.name": "company_name",
            "company.copyright_year": "copyright_year",
            "company.tagline": "company_tagline",
            "company.logo_url": "company_logo_url",
            "company.website": "company_website",
            "editor.name": "editor_name",
            "editor.title": "editor_title",
            "editor.email": "editor_email",
            "editor.signature": "editor_signature",
            "footer.disclaimer": "footer_disclaimer",
            "footer.contact_info": "footer_contact",
            "header.title_prefix": "title_prefix",
            "header.greeting_prefix": "greeting_prefix",
            "audience.description": "audience_description",
            "audience.organization": "audience_organization",
            "style.primary_color": "primary_color",
            "style.secondary_color": "secondary_color",
            "style.font_family": "font_family",
        }

        for path, setting_key in mapping.items():
            value = newsletter_settings.get(setting_key)
            if value is None and path == "company.copyright_year":
                value = str(date.today().year)
            if value is not None:
                self._set_nested_value(config, path, value)

        return config

    def _load_explicit_config(self, config_path: Path) -> dict[str, Any]:
        if config_path.suffix.lower() in {".yml", ".yaml"}:
            with open(config_path, "r", encoding="utf-8") as file_obj:
                config_data = yaml.safe_load(file_obj) or {}
            if not isinstance(config_data, dict):
                return self._default_config()
            newsletter_settings = config_data.get("newsletter_settings", {})
            if isinstance(newsletter_settings, dict):
                return self._build_runtime_config(newsletter_settings)
            return self._default_config()

        with open(config_path, "r", encoding="utf-8") as file_obj:
            config_data = json.load(file_obj)
        if isinstance(config_data, dict):
            return config_data
        return self._default_config()

    @staticmethod
    def _set_nested_value(config: dict[str, Any], path: str, value: Any) -> None:
        parts = path.split(".")
        current: dict[str, Any] = config
        for part in parts[:-1]:
            next_value = current.get(part)
            if not isinstance(next_value, dict):
                next_value = {}
                current[part] = next_value
            current = next_value
        current[parts[-1]] = value

    def get(self, path: str, default: Any = None) -> Any:
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

    def set_config(self, config: dict[str, Any]) -> None:
        """테스트용: 설정을 직접 설정"""
        self._config = config
