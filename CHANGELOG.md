# Changelog

## [0.6.0] - 2025-06-11 - F-14 Centralized Settings Layer 구현

### 🚀 주요 기능

#### 중앙집중식 설정 관리 (F-14)
- **새로운 기능**: Pydantic 기반 타입 안전 설정 시스템
  - `newsletter/centralized_settings.py`: 모든 환경변수의 단일 진실 소스
  - 타입 안전성: int, bool, SecretStr 등 자동 타입 검증 및 변환
  - Fail-Fast 검증: 앱 시작 시점에 필수 설정 누락/오류 즉시 감지
  - 환경별 자동 분기: development/testing/production

#### 보안 강화
- **Secret 마스킹**: 로그에서 API 키 등 시크릿 자동 마스킹
  - `_SecretFilter` 클래스로 로그 출력 시 자동 마스킹
  - SecretStr 타입 사용으로 실수로 인한 노출 방지
  - 시크릿 값 길이 표시로 디버깅 편의성 유지

#### 환경별 설정 지원
- **Development**: `.env` 파일 자동 로드
- **Testing**: GitHub Actions 환경변수 우선
- **Production**: OS 환경변수만 사용, `.env` 파일 무시

#### 호환성 유지
- **레거시 호환 모듈**: `newsletter/compat_env.py`
  - 기존 `os.getenv()` 호출을 점진적 마이그레이션
  - `getenv_compat()` 함수로 중단 없는 전환
  - 마이그레이션 진행도 추적 도구 제공

### 🔧 기술적 개선

#### 설정 검증 강화
- **API 키 길이 검증**: 최소 16자 이상 요구
- **포트 범위 검증**: 1-65535 범위 자동 검증
- **LLM 키 검증**: OpenAI, Anthropic, Gemini 중 최소 1개 필수
- **이메일 설정 검증**: POSTMARK_SERVER_TOKEN, EMAIL_SENDER 필수

#### 코드 마이그레이션 완료
- **핵심 모듈 업데이트**:
  - `newsletter/config_manager.py`: Centralized Settings 우선 사용
  - `web/app.py`: Sentry 설정을 Centralized Settings로 교체
  - `web/worker.py`: Redis 설정을 Centralized Settings로 교체
  - `web/mail.py`: 이메일 설정을 Centralized Settings로 교체

#### 싱글톤 패턴 적용
- `@lru_cache` 데코레이터로 설정 인스턴스 캐싱
- 앱 시작 시 한 번만 로드 & 검증
- 메모리 효율성 및 성능 최적화

### 📁 파일 시스템 개선

#### Docker 보안 강화
- **새로운 파일**: `.dockerignore` 추가
  - `.env*` 패턴으로 환경 파일 누출 방지
  - 이미지 크기 최적화 및 보안 강화

#### 환경변수 문서화
- **새로운 파일**: `env.example` 추가
  - 모든 환경변수 목록과 설명
  - 필수/선택 구분으로 설정 가이드 제공
  - 환경별 설정 예시 및 보안 주의사항

### 🧪 테스트 시스템

#### 단위 테스트 완성
- **새로운 파일**: `tests/unit_tests/test_centralized_settings.py`
  - 설정 검증 테스트: 필수 필드, 타입 검증, 길이 검증
  - 환경별 동작 테스트: development, testing, production
  - 싱글톤 동작 테스트: 캐싱 및 인스턴스 재사용
  - Secret 마스킹 테스트: 로그 필터 동작 검증

### 📚 문서화 완성

#### README 업데이트
- **Settings 섹션 추가**: F-14 기능 상세 설명
  - 환경변수 우선순위 명시
  - 사용 방법 및 예시 코드
  - 환경별 설정 가이드
  - 마이그레이션 가이드

### 🎯 완료된 체크리스트

#### 1-A. Settings Core
- ✅ 설계 내용 기존 문서에 통합
- ✅ settings.py 스캐폴딩 (Pydantic 기반)
- ✅ Fail-Fast 검증 로직 (포트, 키 길이, LLM 키)
- ✅ 싱글턴 헬퍼 (`@lru_cache get_settings()`)
- ✅ Secret 마스킹 로거 (`_SecretFilter`)
- ✅ env-compat shim (`newsletter/compat_env.py`)
- ✅ 레거시 호출 교체 (핵심 모듈 우선)

#### 1-B. 환경별 분기 & DevOps
- ✅ `.dockerignore` 추가 (`.env*` 누출 방지)
- ✅ `env.example` 강화 (상세 설명 및 구역 분리)

#### 1-C. 테스트 & 보안
- ✅ Unit 테스트 (happy/error/masking 케이스)
- ✅ Secret 마스킹 검증

#### 1-D. 문서화
- ✅ README "⚙️ Settings" 섹션 추가
- ✅ 환경변수 설정 가이드 업데이트
- ✅ CHANGELOG 항목 추가

### 🔧 Breaking Changes
- 없음 (완전한 하위 호환성 유지)

### 🌟 검증 결과

#### 환경별 테스트
- ✅ Development: `.env` 파일 로드 + 자동 검증
- ✅ Testing: 필수 환경변수 누락 시 즉시 실패
- ✅ Production: OS 환경변수만 사용, 보안 강화

#### 호환성 테스트
- ✅ 기존 CLI: `python -m newsletter.cli` 정상 동작
- ✅ 웹 애플리케이션: 모든 기능 정상 동작
- ✅ 레거시 코드: `getenv_compat()` 을 통한 안전한 마이그레이션

---

## [0.5.1] - 2025-06-09 - F-03 즉시 이메일 발송 기능 완성

### 🚀 주요 기능

#### 웹 인터페이스 즉시 이메일 발송
- **새로운 기능**: 웹에서 뉴스레터 생성 시 즉시 이메일 발송
  - 선택적 이메일 입력 필드 추가 (RFC-5322 검증)
  - 실시간 진행 상태 표시 및 이메일 발송 완료 알림
  - 비동기 작업 처리로 사용자 경험 개선

#### 백엔드 API 개선
- **API 확장**: `/api/generate` 엔드포인트 개선
  - Pydantic v2 기반 입력 스키마 검증
  - 이메일 주소 RFC-5322 정규표현식 검증
  - 비동기 작업 큐 처리 (Redis Queue 사용)
  - HTTP 202 응답으로 즉시 job_id 반환

#### 프론트엔드 UX 개선
- **실시간 업데이트**: 1초 간격 상태 폴링
- **직관적 UI**: 이메일 입력 필드 "(선택)" 뱃지 표시
- **피드백 시스템**: 이메일 발송 완료 토스트 알림

### 🔧 기술적 개선

#### 코드 아키텍처 정리
- **중복 모듈 제거**: `newsletter/email.py` 삭제
  - 기존 `web/mail.py` 모듈 활용으로 단일화
  - Postmark API 통합으로 일관성 있는 이메일 발송

#### 타입 안전성 강화
- **새로운 타입 모듈**: `web/types.py` 추가
  - `EmailAddress` NewType 정의
  - Pydantic v2 호환 스키마 구현
  - 이메일 주소 유효성 검증 강화

#### 테스트 완성도 향상
- **단위 테스트**: `tests/test_web_mail.py` 추가
  - Postmark API 200/422 응답 모킹
  - 이메일 발송 성공/실패 케이스 검증
- **통합 테스트**: `tests/test_web_api.py` 추가
  - API 워크플로우 전체 테스트
  - 이메일 발송 포함 완전한 시나리오 검증

### 📚 문서화

#### 사용자 가이드
- **새로운 문서**: `docs/user/email-sending.md` 추가
  - 웹 인터페이스 사용 방법
  - API 사용 예시
  - 문제 해결 가이드
  - 보안 고려사항

### 🎯 완료된 기능

#### 체크리스트
- ✅ 중복 모듈 제거 (`newsletter/email.py`)
- ✅ 레거시 코드 참조 정리
- ✅ 공통 타입 정의 (`web/types.py`)
- ✅ 백엔드 API 개선 (`/api/generate`)
- ✅ 프론트엔드 UI/UX 연결
- ✅ 단위 테스트 구현
- ✅ 통합 테스트 구현
- ✅ 사용자 문서 작성

### 🔧 Breaking Changes
- 없음 (하위 호환성 완전 유지)

---

## [0.5.0] - 2025-06-04 - ConfigManager 도입 및 테스트 구조 개선

### 🏗️ 주요 개선사항

#### ConfigManager 중앙 집중식 설정 관리
- **새로운 기능**: `newsletter/config_manager.py` 추가
  - 싱글톤 패턴으로 설정 관리 중앙화
  - 환경변수 로딩 및 캐싱 최적화
  - 테스트용 `reset_for_testing()` 메서드 제공
  - YAML 설정 파일 통합 관리

#### 이메일 설정 통합
- **중복 제거**: `EMAIL_SENDER`와 `POSTMARK_FROM_EMAIL` 통합
  - `EMAIL_SENDER`로 단일화
  - 하위 호환성 유지
  - `web/mail.py`에서 ConfigManager 사용

#### 테스트 구조 대폭 개선
- **테스트 디렉토리 재구성**:
  ```
  tests/
  ├── unit_tests/          # 단위 테스트
  ├── integration/         # 통합 테스트  
  ├── manual/              # 수동 테스트
  └── api_tests/           # API 테스트
  ```

- **pytest 마커 시스템 도입**:
  - `@pytest.mark.manual`: 수동 테스트
  - `@pytest.mark.real_api`: 실제 API 테스트
  - `@pytest.mark.mock_api`: Mock API 테스트
  - `@pytest.mark.integration`: 통합 테스트

#### 테스트 품질 개선
- **ConfigManager 테스트**: 완전한 단위 테스트 커버리지
- **메일 테스트 개선**: 실제 API 호출 방지, 모킹 강화
- **필수 테스트 스크립트**: `tests/run_essential_tests.py` 추가

### 🔧 기술적 개선

#### 설정 로딩 최적화
- **Before**: 각 모듈에서 개별적으로 YAML 파싱
- **After**: ConfigManager에서 중앙 집중식 캐싱

#### 테스트 격리 개선
- **Before**: 환경변수 상태 공유로 테스트 간섭
- **After**: `reset_for_testing()`으로 완전한 격리

#### 코드 중복 제거
- **Before**: 설정 로딩 로직이 여러 파일에 분산
- **After**: ConfigManager로 단일 책임 원칙 적용

### 📊 성능 개선
- 설정 캐싱으로 반복 로딩 방지
- 테스트 실행 시간 단축
- 메모리 사용량 최적화

### 🚨 Breaking Changes
- 없음 (하위 호환성 완전 유지)

### 📝 문서 업데이트
- `tests/README.md`: 새로운 테스트 구조 문서화
- 테스트 실행 가이드 개선
- 문제 해결 섹션 추가

### 🎯 다음 단계
- [ ] 추가 모듈의 ConfigManager 마이그레이션
- [ ] 성능 모니터링 및 최적화
- [ ] 테스트 커버리지 확대

---

## [0.4.1] - 2025-05-29 - Debug 파일 관리 개선

### Improved
- **🗂️ Debug 파일 관리 개선**
  - template_debug_*.txt 파일이 처음부터 `debug_files/` 디렉토리에 생성되도록 변경
  - `debug_files/` 디렉토리가 없을 경우 자동 생성하는 알고리즘 추가
  - `newsletter/utils/file_naming.py`에 debug 파일 관리 유틸리티 함수 추가:
    - `ensure_debug_directory()`: debug_files 디렉토리 확인 및 생성
    - `generate_debug_filename()`: debug 파일명 생성
    - `save_debug_file()`: debug 파일 저장
  - `newsletter/chains.py`에서 새로운 유틸리티 함수 사용
  - 프로젝트 루트 디렉토리가 깔끔하게 유지됨

### Fixed
- Debug 파일 생성 시 프로젝트 루트 디렉토리에 파일이 쌓이는 문제 해결
- 디렉토리 생성 실패로 인한 오류 방지

---

## [0.4.0] - 2025-05-26 - 멀티 LLM 제공자 지원

### Added
- **멀티 LLM 제공자 지원 시스템 구축**
  - Google Gemini, Anthropic Claude, OpenAI GPT 통합 지원
  - 기능별 최적화된 LLM 모델 선택 시스템 구현
  - LLM Factory 패턴으로 제공자 관리 통합
  - 자동 Fallback 메커니즘으로 안정성 향상

- **기능별 세밀한 LLM 설정**
  - 키워드 생성: Claude (창의성 중시)
  - 테마 추출: Gemini Flash (빠른 분석)
  - 뉴스 요약: Gemini Pro (정확성 중시)
  - 섹션 재생성: Claude (구조화 작업)
  - 소개 생성: Claude (자연스러운 글쓰기)
  - HTML 생성: Gemini Pro (복잡한 구조화)
  - 기사 점수: Gemini Flash (빠른 판단)
  - 번역: Gemini Pro (정확성)

- **LLM 테스트 및 검증 도구**
  - `test_llm.py`: 기본 LLM 시스템 상태 확인
  - `test_llm_providers.py`: 제공자별 상세 테스트
  - 실시간 응답 테스트 및 성능 검증

### Changed
- **LLM 설정 구조 개선**
  - `config.yml`에서 제공자별/기능별 세밀한 설정 지원
  - Temperature, timeout, max_retries 등 매개변수 최적화
  - 제공자별 모델 티어 시스템 (fast/standard/advanced)

- **비용 최적화**
  - 작업 특성에 맞는 모델 자동 선택
  - Flash/Haiku 모델로 빠른 작업 처리
  - Pro/Sonnet 모델로 정확한 작업 처리

### Fixed
- **모델 호환성 문제 해결**
  - 최신 Claude 모델명으로 업데이트
  - 404 오류 발생 모델 교체
  - API 키 검증 및 오류 처리 개선

### Documentation
- **[🤖 LLM 설정 가이드](docs/technical/LLM_CONFIGURATION.md)** 추가
  - 다양한 LLM 제공자 설정 방법
  - 기능별 모델 선택 가이드
  - 비용 최적화 팁
  - 문제 해결 방법
- **README.md** 업데이트: 멀티 LLM 지원 정보 추가
- **env.example** 파일 추가: 환경변수 설정 예시

---

## [0.3.0] - 2025-05-25 - GitHub Actions CI/CD 파이프라인

### Added
- **GitHub Actions CI/CD 파이프라인 구축**
  - CI 워크플로우: Python 3.10, 3.11 매트릭스 테스트
  - 코드 품질 워크플로우: Black, isort, flake8, mypy 검사
  - 도구 테스트 워크플로우: 특정 파일 변경 시 자동 테스트
  - 뉴스레터 생성 워크플로우: 스케줄 기반 자동 생성 및 GitHub Pages 배포

- **의존성 관리 최적화**
  - `requirements-minimal.txt`: CI용 최소 의존성
  - `requirements-dev.txt`: 개발 및 테스트 도구
  - `pyproject.toml`: 현대적인 Python 패키징 설정 완성

- **테스트 인프라 개선**
  - CI 환경에서 안정적인 테스트 실행을 위한 스크립트 추가
  - Mock API 기반 테스트로 외부 의존성 제거
  - gRPC 환경 설정 최적화

### Changed
- **Python 버전 요구사항 업데이트**
  - 최소 Python 버전을 3.8에서 3.10으로 상향 조정
  - GitHub Actions에서 Python 3.10, 3.11 매트릭스 테스트

- **프로젝트 구조 개선**
  - `setup.py` 간소화 (pyproject.toml 중심으로 전환)
  - CI/CD 관련 스크립트 및 설정 파일 추가

### Fixed
- **GitHub Actions 호환성 문제 해결**
  - Actions 버전을 최신으로 업데이트 (v4, v5)
  - YAML 문법 오류 수정
  - 환경 변수 설정 개선

- **의존성 충돌 해결**
  - setup.py와 pyproject.toml 간 충돌 제거
  - 패키지 설치 순서 최적화

### Documentation
- **README.md 대폭 개선**
  - CI/CD 배지 추가
  - 개발자를 위한 CI/CD 정보 섹션 추가
  - Pull Request 체크리스트 및 배포 프로세스 문서화
  - 디버깅 및 문제 해결 가이드 추가

---

## [0.2.2] - 2025-05-19 - Gemini 2.5 Pro 업그레이드

### Changed
- Gemini 2.5 Pro 모델로 업그레이드
  - 모든 LLM 인스턴스를 Gemini 2.5 Pro/Flash 모델로 변경
  - 비용 계산 로직 업데이트 (새로운 단가 반영)
  - `get_summarization_chain` 함수에 callbacks 매개변수 지원 추가

### Fixed
- LangGraph 워크플로우 에러 수정
  - 요약 단계에서 데이터 구조 불일치 문제 해결
  - 뉴스레터 작성 완료 단계 추가 
  - 최종 HTML 파일 저장 기능 자동화

---

## [0.2.1] - 2025-05-19 - 호환성 문제 해결

### Fixed
- LangSmith 및 Google Generative AI 호환성 문제 해결
  - `request_timeout` → `timeout`으로 매개변수 이름 변경
  - `streaming` → `disable_streaming`으로 매개변수 이름 변경 
  - LangSmith Client API 변경사항 반영 (`get_tracing_callback` → `LangChainTracer` 직접 생성)
  - 프롬프트 형식 수정으로 들여쓰기 문제 해결

---

## [0.2.0] - 2025-05-15 - LangSmith 통합 및 비용 추적

### Added
- `GoogleGenAICostCB` 클래스 추가: Google Generative AI 모델의 토큰 사용량 및 비용 추적
- 새로운 설정 매개변수:
  - `timeout=60`: API 요청 타임아웃 60초로 설정
  - `max_retries=2`: 최대 2회 재시도
  - `disable_streaming=False`: 응답 스트리밍으로 블로킹 방지
- `docs/langsmith_setup.md`: LangSmith 연동 및 비용 추적 설정 가이드 문서 추가

### Changed
- `cost_tracking.py`: 기존 콜백 핸들러 개선 및 새 콜백 클래스 추가
- `chains.py`: LLM 초기화 설정 개선
- `tools.py`: 키워드 생성 및 테마 추출 함수 업데이트
- `graph.py`: LangGraph 워크플로우에 비용 추적 통합

### Fixed
- LangSmith 통합 및 비용 추적 개선
  - LangChain 0.3+ 버전 환경 변수 지원 (`LANGCHAIN_*` 계열)
  - Google Generative AI용 비용 추적 콜백 구현
  - 무한 대기 방지를 위한 타임아웃 및 재시도 설정 추가
  - 스트리밍 모드 활성화로 블로킹 방지

---

## [0.1.0] - 2025-05-09 - 최초 릴리스

### Added
- 최초 릴리스
- 뉴스 수집 및 요약 기능
- HTML 및 Markdown 형식 뉴스레터 생성
- 중복 기사 감지 및 제거
- 주요 뉴스 소스 우선순위 필터링
- 키워드별 기사 그룹화 