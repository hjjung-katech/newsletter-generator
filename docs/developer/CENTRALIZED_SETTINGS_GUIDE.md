# 🛠️ F-14 Centralized Settings Layer - Developer Guide

> **F-14 중앙집중식 설정 시스템 개발자 가이드**
> 설정 필드 추가/변경, 테스트, 모범 사례

## 📋 목차

1. [개요](#개요)
2. [설정 필드 추가 절차](#설정-필드-추가-절차)
3. [설정 필드 변경 절차](#설정-필드-변경-절차)
4. [테스트 방법](#테스트-방법)
5. [모범 사례](#모범-사례)
6. [문제 해결](#문제-해결)

---

## 🎯 개요

F-14 Centralized Settings Layer는 애플리케이션의 모든 환경변수를 중앙에서 관리하는 타입 안전한 시스템입니다.

### 주요 구성 요소

- **`newsletter/centralized_settings.py`**: 메인 설정 모듈
- **`newsletter/compat_env.py`**: 레거시 호환 레이어
- **`newsletter/config_manager.py`**: 기존 ConfigManager와의 통합
- **`.env.example`**: 환경변수 문서화

---

## ➕ 설정 필드 추가 절차

### 1단계: 설정 클래스에 필드 추가

`newsletter/centralized_settings.py`의 `CentralizedSettings` 클래스에 필드를 추가합니다.

```python
class CentralizedSettings(BaseSettings):
    # 기존 필드들...

    # 새로운 필드 추가
    new_feature_api_key: SecretStr | None = None
    new_feature_enabled: bool = Field(False, description="새 기능 활성화 여부")
    new_feature_timeout: int = Field(30, ge=1, le=300, description="타임아웃 (초)")
```

### 2단계: 필드 검증 추가 (필요시)

```python
@field_validator("new_feature_api_key")
@classmethod
def _validate_new_feature_key(cls, v: SecretStr | None) -> SecretStr | None:
    """새 기능 API 키 검증"""
    if v is not None and len(v.get_secret_value()) < 20:
        raise ValueError("New feature API key must be ≥ 20 characters")
    return v
```

### 3단계: 레거시 호환성 추가

`newsletter/compat_env.py`의 `mapping` 딕셔너리에 추가:

```python
mapping = {
    # 기존 매핑들...
    "new_feature_api_key": lambda s: (
        s.new_feature_api_key.get_secret_value()
        if s.new_feature_api_key else None
    ),
    "new_feature_enabled": lambda s: s.new_feature_enabled,
    "new_feature_timeout": lambda s: s.new_feature_timeout,
}
```

### 4단계: ConfigManager 통합 (필요시)

`newsletter/config_manager.py`에서 필요한 경우 필드를 추가:

```python
def _load_environment_variables(self):
    try:
        from newsletter.centralized_settings import get_settings
        settings = get_settings()

        # 기존 필드들...
        self.NEW_FEATURE_API_KEY = (
            settings.new_feature_api_key.get_secret_value()
            if settings.new_feature_api_key else None
        )
        self.NEW_FEATURE_ENABLED = settings.new_feature_enabled

    except Exception:
        # Fallback
        self.NEW_FEATURE_API_KEY = getenv_compat("NEW_FEATURE_API_KEY")
        self.NEW_FEATURE_ENABLED = getenv_compat("NEW_FEATURE_ENABLED", "false").lower() == "true"
```

### 5단계: 문서 업데이트

#### `.env.example` 업데이트:
```bash
# ===========================================
# 🆕 New Feature Configuration
# ===========================================
# NEW_FEATURE_API_KEY=your-new-feature-api-key-here
# NEW_FEATURE_ENABLED=true
# NEW_FEATURE_TIMEOUT=60
```

#### `README.md` 업데이트:
```markdown
### 새 기능 설정

- `NEW_FEATURE_API_KEY`: 새 기능용 API 키 (선택사항)
- `NEW_FEATURE_ENABLED`: 새 기능 활성화 (기본값: false)
- `NEW_FEATURE_TIMEOUT`: 타임아웃 설정 (기본값: 30초)
```

### 6단계: 테스트 작성

```python
def test_new_feature_configuration(self):
    """새 기능 설정 테스트"""
    env_vars = {
        "SERPER_API_KEY": "test-key-1234567890123456",
        "POSTMARK_SERVER_TOKEN": "test-token-1234567890123456",
        "EMAIL_SENDER": "test@example.com",
        "OPENAI_API_KEY": "sk-test-1234567890123456",
        "NEW_FEATURE_API_KEY": "new-feature-key-12345678901234567890",
        "NEW_FEATURE_ENABLED": "true",
        "NEW_FEATURE_TIMEOUT": "60",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        settings = CentralizedSettings()
        assert settings.new_feature_enabled is True
        assert settings.new_feature_timeout == 60
        assert settings.new_feature_api_key.get_secret_value() == env_vars["NEW_FEATURE_API_KEY"]
```

---

## ✏️ 설정 필드 변경 절차

### 필드 타입 변경

```python
# 이전
old_field: str = "default"

# 변경 후 (하위 호환성 유지)
old_field: str | int = Field("default", description="Old field with new type support")

@field_validator("old_field", mode="before")
@classmethod
def _convert_old_field(cls, v):
    """이전 타입에서 새 타입으로 변환"""
    if isinstance(v, str) and v.isdigit():
        return int(v)
    return v
```

### 필드 이름 변경

```python
# 새 필드 추가 + 기존 필드 별칭 유지
new_field_name: str = Field(..., alias="old_field_name")

# 또는 속성으로 하위 호환성 제공
@property
def old_field_name(self) -> str:
    """하위 호환성을 위한 기존 필드명"""
    return self.new_field_name
```

### 필수 필드를 선택 필드로 변경

```python
# 이전
required_field: str = Field(...)

# 변경 후
required_field: str = Field("sensible_default", description="Now optional with default")
```

---

## 🧪 테스트 방법

### 단위 테스트

```bash
# 설정 테스트만 실행
python -m pytest tests/unit_tests/test_centralized_settings.py -v

# 특정 테스트 실행
python -m pytest tests/unit_tests/test_centralized_settings.py::TestCentralizedSettings::test_happy_path -v
```

### 환경별 통합 테스트

```bash
# 통합 테스트 활성화하여 실행
RUN_INTEGRATION_TESTS=1 python -m pytest tests/integration/test_environment_profiles.py -v
```

### 설정 검증 테스트

```python
def test_local_settings_validation():
    """로컬 환경에서 설정 검증"""
    from newsletter.centralized_settings import get_settings

    try:
        settings = get_settings()
        print("✅ Settings validation passed")
        print(f"📊 Config summary: {settings.get_config_summary()}")
    except Exception as e:
        print(f"❌ Settings validation failed: {e}")
```

### 마이그레이션 진행도 확인

```python
from newsletter.compat_env import report_migration_status

# os.getenv 사용 현황 리포트
report_migration_status()
```

---

## 📝 모범 사례

### 1. 필드 정의 원칙

```python
class CentralizedSettings(BaseSettings):
    # ✅ 좋은 예
    api_timeout: int = Field(
        30,
        ge=1,
        le=300,
        description="API 타임아웃 (초, 1-300 범위)"
    )

    feature_enabled: bool = Field(
        False,
        description="기능 활성화 여부"
    )

    secret_key: SecretStr = Field(
        ...,
        min_length=32,
        description="32자 이상의 비밀 키"
    )

    # ❌ 피해야 할 예
    timeout: int = 30  # 설명과 검증 없음
    key: str  # 타입만 명시, 보안 고려 없음
```

### 2. 검증 메서드 작성

```python
@field_validator("custom_field")
@classmethod
def _validate_custom_field(cls, v: str) -> str:
    """커스텀 필드 검증

    Args:
        v: 검증할 값

    Returns:
        str: 검증된 값

    Raises:
        ValueError: 검증 실패 시
    """
    if not v.startswith("custom_"):
        raise ValueError("Custom field must start with 'custom_'")
    return v
```

### 3. 환경별 기본값

```python
# 환경별 조건부 기본값
debug: bool = Field(
    default_factory=lambda: os.getenv("APP_ENV") == "development",
    description="디버그 모드 (development 환경에서 자동 활성화)"
)
```

### 4. Secret 관리

```python
# ✅ 보안 필드
secret_api_key: SecretStr = Field(..., description="API 비밀 키")

# ✅ 선택적 보안 필드
optional_secret: SecretStr | None = None

# ❌ 일반 문자열로 비밀 정보 저장
api_key: str = Field(...)  # 보안 위험!
```

---

## 🔧 문제 해결

### 흔한 오류와 해결책

#### 1. ValidationError: field required

```python
# 원인: 필수 필드가 환경변수에 없음
# 해결: 환경변수 설정 또는 기본값 제공

# 임시 해결책
my_field: str = Field("temporary_default")

# 근본 해결책
export MY_FIELD=production_value
```

#### 2. ValueError: must be ≥ 16 characters

```python
# 원인: API 키 길이 검증 실패
# 해결: 올바른 길이의 키 사용

export SERPER_API_KEY=your-actual-long-api-key-here
```

#### 3. ImportError: No module named 'pydantic_settings'

```bash
# 해결: 의존성 설치
pip install pydantic-settings
```

### 디버깅 도구

#### 설정 상태 확인

```python
from newsletter.centralized_settings import get_settings

settings = get_settings()
print("📊 Current settings:")
print(settings.get_config_summary())
```

#### 환경변수 우선순위 확인

```python
import os
from newsletter.centralized_settings import get_settings

settings = get_settings()
print(f"🌍 Current environment: {settings.app_env}")
print(f"🔍 Environment variables:")
for key in ["SERPER_API_KEY", "OPENAI_API_KEY", "APP_ENV"]:
    value = os.getenv(key, "NOT_SET")
    masked = "•••••••" if "KEY" in key and value != "NOT_SET" else value
    print(f"  {key}: {masked}")
```

### 마이그레이션 가이드

#### 기존 코드에서 새 시스템으로

```python
# 이전 방식
import os
api_key = os.getenv("SERPER_API_KEY")

# 임시 호환 방식
from newsletter.compat_env import getenv_compat
api_key = getenv_compat("SERPER_API_KEY")

# 새로운 방식 (권장)
from newsletter.centralized_settings import get_settings
settings = get_settings()
api_key = settings.serper_api_key.get_secret_value()
```

---

## 📚 추가 참고 자료

- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [F-14 구현 상세 (archive)](../archive/2026-q1/F14_COMPLETION_REPORT.md)
- [환경변수 예시 (.env.example)](../../.env.example)
- [테스트 예제 (tests/unit_tests/test_centralized_settings.py)](../../tests/unit_tests/test_centralized_settings.py)

---

## 🏷️ 버전 정보

- **구현 버전**: v0.6.0
- **최종 업데이트**: 2025-06-11
- **호환성**: Python 3.10+, Pydantic 2.0+
