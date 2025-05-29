# Changelog

## [0.4.1] - 2025-05-29

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

## [0.4.0] - 2025-05-26

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

## [0.3.0] - 2025-05-25

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

## [0.2.2] - 2025-05-19

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

## [0.2.1] - 2025-05-19

### Fixed
- LangSmith 및 Google Generative AI 호환성 문제 해결
  - `request_timeout` → `timeout`으로 매개변수 이름 변경
  - `streaming` → `disable_streaming`으로 매개변수 이름 변경 
  - LangSmith Client API 변경사항 반영 (`get_tracing_callback` → `LangChainTracer` 직접 생성)
  - 프롬프트 형식 수정으로 들여쓰기 문제 해결

## [0.2.0] - 2025-05-15

### Fixed
- LangSmith 통합 및 비용 추적 개선
  - LangChain 0.3+ 버전 환경 변수 지원 (`LANGCHAIN_*` 계열)
  - Google Generative AI용 비용 추적 콜백 구현
  - 무한 대기 방지를 위한 타임아웃 및 재시도 설정 추가
  - 스트리밍 모드 활성화로 블로킹 방지

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

## [0.1.0] - 2025-05-09

### Added
- 최초 릴리스
- 뉴스 수집 및 요약 기능
- HTML 및 Markdown 형식 뉴스레터 생성
- 중복 기사 감지 및 제거
- 주요 뉴스 소스 우선순위 필터링
- 키워드별 기사 그룹화 