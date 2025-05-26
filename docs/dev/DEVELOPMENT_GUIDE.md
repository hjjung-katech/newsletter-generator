# 개발자 가이드

Newsletter Generator 프로젝트에 기여하고 개발하기 위한 종합적인 가이드입니다.

## 📋 목차

1. [개발 환경 설정](#개발-환경-설정)
2. [프로젝트 구조](#프로젝트-구조)
3. [개발 워크플로우](#개발-워크플로우)
4. [코딩 스타일](#코딩-스타일)
5. [테스트](#테스트)
6. [디버깅](#디버깅)
7. [기여 방법](#기여-방법)
8. [릴리스 프로세스](#릴리스-프로세스)

## 개발 환경 설정

### 필수 도구

- **Python 3.10+**: 메인 개발 언어
- **Git**: 버전 관리
- **IDE**: VS Code, PyCharm 등 (권장: VS Code)
- **Docker**: 컨테이너 테스트용 (선택사항)

### 개발 환경 구성

```bash
# 1. 저장소 포크 및 클론
git clone https://github.com/your-username/newsletter-generator.git
cd newsletter-generator

# 2. 업스트림 리모트 추가
git remote add upstream https://github.com/original-org/newsletter-generator.git

# 3. 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# 4. 개발 의존성 설치
pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -e .

# 5. pre-commit 훅 설치
pre-commit install
```

### IDE 설정

#### VS Code 설정

`.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.sortImports.args": ["--profile", "black"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

#### 권장 VS Code 확장

- Python
- Black Formatter
- isort
- Pylance
- GitLens
- Markdown All in One

## 프로젝트 구조

```
newsletter-generator/
├── .github/                    # GitHub Actions 워크플로우
│   └── workflows/
├── docs/                       # 문서
│   ├── dev/                   # 개발자 문서
│   ├── user/                  # 사용자 문서
│   ├── setup/                 # 설정 가이드
│   └── technical/             # 기술 문서
├── newsletter/                 # 메인 패키지
│   ├── __init__.py
│   ├── cli.py                 # CLI 인터페이스
│   ├── collect.py             # 뉴스 수집
│   ├── compose.py             # 뉴스레터 조합
│   ├── chains.py              # LangChain 체인
│   ├── graph.py               # LangGraph 워크플로우
│   ├── deliver.py             # 배송 (이메일, Drive)
│   ├── tools.py               # 유틸리티 도구
│   ├── cost_tracking.py       # 비용 추적
│   └── utils/                 # 유틸리티 모듈
├── templates/                  # HTML 템플릿
├── tests/                      # 테스트 파일
│   ├── unit_tests/            # 단위 테스트
│   ├── api_tests/             # API 테스트
│   └── test_data/             # 테스트 데이터
├── output/                     # 생성된 파일
├── config/                     # 설정 파일
├── requirements.txt            # 프로덕션 의존성
├── requirements-dev.txt        # 개발 의존성
├── requirements-minimal.txt    # 최소 의존성
├── pyproject.toml             # 프로젝트 설정
├── setup.py                   # 패키지 설정
├── .pre-commit-config.yaml    # pre-commit 설정
└── run_tests.py               # 테스트 실행 스크립트
```

### 핵심 모듈 설명

#### `newsletter/cli.py`
- Typer 기반 CLI 인터페이스
- 명령어 파싱 및 실행 조정

#### `newsletter/collect.py`
- 다양한 뉴스 소스에서 기사 수집
- Serper API, RSS 피드, 네이버 API 통합

#### `newsletter/compose.py`
- 통합 뉴스레터 조합 로직
- Compact/Detailed 스타일 지원

#### `newsletter/graph.py`
- LangGraph 기반 워크플로우 정의
- 상태 관리 및 노드 실행

#### `newsletter/chains.py`
- LangChain 체인 정의
- LLM 프롬프트 및 응답 처리

## 개발 워크플로우

### 브랜치 전략

```bash
# 메인 브랜치
main                    # 안정 버전
develop                 # 개발 브랜치

# 기능 브랜치
feature/feature-name    # 새 기능
bugfix/bug-description  # 버그 수정
hotfix/urgent-fix      # 긴급 수정
```

### 개발 프로세스

1. **이슈 생성**: GitHub Issues에서 작업 내용 정의
2. **브랜치 생성**: 기능별 브랜치 생성
3. **개발**: 코드 작성 및 테스트
4. **커밋**: 의미 있는 커밋 메시지 작성
5. **푸시**: 원격 브랜치에 푸시
6. **PR 생성**: Pull Request 생성
7. **코드 리뷰**: 팀원 리뷰 및 피드백
8. **병합**: 승인 후 메인 브랜치 병합

### 커밋 메시지 규칙

```bash
# 형식: type(scope): description

feat(cli): add new --template-style option
fix(collect): resolve RSS feed parsing error
docs(readme): update installation instructions
test(compose): add unit tests for newsletter composition
refactor(graph): simplify workflow state management
```

#### 커밋 타입

- `feat`: 새 기능
- `fix`: 버그 수정
- `docs`: 문서 변경
- `test`: 테스트 추가/수정
- `refactor`: 코드 리팩토링
- `style`: 코드 스타일 변경
- `chore`: 빌드/도구 변경

## 코딩 스타일

### Python 스타일 가이드

프로젝트는 다음 도구들을 사용하여 일관된 코드 스타일을 유지합니다:

- **Black**: 코드 포맷팅
- **isort**: import 정렬
- **flake8**: 린팅
- **mypy**: 타입 검사

### 코드 품질 검사

```bash
# 모든 품질 검사 실행
python run_tests.py quality

# 개별 도구 실행
black newsletter tests                    # 포맷팅
isort newsletter tests                    # import 정렬
flake8 newsletter tests                   # 린팅
mypy newsletter                          # 타입 검사
```

### 타입 힌트

모든 함수와 메서드에 타입 힌트를 추가하세요:

```python
from typing import List, Dict, Optional, Union
from pathlib import Path

def collect_articles(
    keywords: List[str], 
    period_days: int = 14,
    max_per_source: Optional[int] = None
) -> Dict[str, List[Dict[str, str]]]:
    """뉴스 기사를 수집합니다."""
    pass
```

### 문서화

#### Docstring 스타일

Google 스타일 docstring을 사용합니다:

```python
def compose_newsletter(
    data: Dict[str, Any], 
    template_dir: str, 
    style: str = "detailed"
) -> str:
    """뉴스레터를 생성하는 통합 함수.
    
    Args:
        data: 뉴스레터 데이터
        template_dir: 템플릿 디렉토리 경로
        style: 뉴스레터 스타일 ("compact" 또는 "detailed")
    
    Returns:
        str: 렌더링된 HTML 뉴스레터
        
    Raises:
        ValueError: 잘못된 스타일이 제공된 경우
        FileNotFoundError: 템플릿 파일을 찾을 수 없는 경우
    """
    pass
```

## 테스트

### 테스트 구조

```
tests/
├── unit_tests/              # 단위 테스트
│   ├── test_collect.py     # 수집 모듈 테스트
│   ├── test_compose.py     # 조합 모듈 테스트
│   └── test_tools.py       # 도구 모듈 테스트
├── api_tests/              # API 통합 테스트
│   ├── test_serper.py      # Serper API 테스트
│   └── test_gemini.py      # Gemini API 테스트
└── test_data/              # 테스트 데이터
    ├── sample_articles.json
    └── mock_responses/
```

### 테스트 실행

```bash
# 모든 테스트 실행
python run_tests.py all

# 환경별 테스트
python run_tests.py dev      # 개발 환경
python run_tests.py ci       # CI 환경
python run_tests.py prod     # 프로덕션 환경

# 특정 테스트 파일
pytest tests/unit_tests/test_compose.py

# 커버리지 포함
pytest --cov=newsletter tests/
```

### 테스트 작성 가이드

#### 단위 테스트 예시

```python
import pytest
from unittest.mock import Mock, patch
from newsletter.compose import compose_newsletter

class TestComposeNewsletter:
    """뉴스레터 조합 함수 테스트."""
    
    def test_compose_newsletter_detailed_style(self):
        """Detailed 스타일 뉴스레터 생성 테스트."""
        # Given
        mock_data = {
            "articles": [{"title": "Test", "content": "Content"}],
            "keywords": ["AI"]
        }
        template_dir = "templates"
        
        # When
        result = compose_newsletter(mock_data, template_dir, "detailed")
        
        # Then
        assert isinstance(result, str)
        assert "Test" in result
        
    @patch('newsletter.compose.render_template')
    def test_compose_newsletter_with_mock(self, mock_render):
        """Mock을 사용한 테스트."""
        # Given
        mock_render.return_value = "<html>Mock Newsletter</html>"
        
        # When
        result = compose_newsletter({}, "templates", "compact")
        
        # Then
        assert result == "<html>Mock Newsletter</html>"
        mock_render.assert_called_once()
```

#### API 테스트 예시

```python
import pytest
import responses
from newsletter.collect import collect_from_serper

class TestSerperAPI:
    """Serper API 테스트."""
    
    @responses.activate
    def test_collect_from_serper_success(self):
        """Serper API 성공 응답 테스트."""
        # Given
        responses.add(
            responses.POST,
            "https://google.serper.dev/search",
            json={"organic": [{"title": "Test", "link": "http://test.com"}]},
            status=200
        )
        
        # When
        result = collect_from_serper(["AI"], api_key="test_key")
        
        # Then
        assert len(result) == 1
        assert result[0]["title"] == "Test"
```

### 테스트 데이터 관리

```python
# tests/conftest.py
import pytest
import json
from pathlib import Path

@pytest.fixture
def sample_articles():
    """샘플 기사 데이터."""
    test_data_path = Path(__file__).parent / "test_data" / "sample_articles.json"
    with open(test_data_path) as f:
        return json.load(f)

@pytest.fixture
def mock_api_response():
    """Mock API 응답."""
    return {
        "status": "success",
        "data": [{"title": "Test Article", "url": "http://example.com"}]
    }
```

## 디버깅

### 로깅 설정

```python
import logging

# 개발 중 디버그 로깅 활성화
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.debug("Debug message")
```

### 디버깅 도구

#### 1. pdb 사용

```python
import pdb

def problematic_function():
    data = get_data()
    pdb.set_trace()  # 브레이크포인트
    processed = process_data(data)
    return processed
```

#### 2. VS Code 디버거

`.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Newsletter CLI",
            "type": "python",
            "request": "launch",
            "module": "newsletter.cli",
            "args": ["run", "--keywords", "AI", "--output-format", "html"],
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        }
    ]
}
```

#### 3. 중간 결과 저장

```bash
# 디버깅용 중간 결과 저장
newsletter run --keywords "AI" --save-intermediate --verbose
```

### 성능 프로파일링

```python
import cProfile
import pstats

def profile_function():
    """함수 성능 프로파일링."""
    profiler = cProfile.Profile()
    profiler.enable()
    
    # 프로파일링할 코드
    result = expensive_function()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # 상위 10개 함수
    
    return result
```

## 기여 방법

### Pull Request 가이드

#### PR 체크리스트

- [ ] 이슈와 연결되어 있음
- [ ] 코드 품질 검사 통과
- [ ] 테스트 추가/업데이트
- [ ] 문서 업데이트 (필요한 경우)
- [ ] CHANGELOG.md 업데이트

#### PR 템플릿

```markdown
## 변경 사항

- 새 기능/버그 수정/개선 사항 설명

## 관련 이슈

Closes #123

## 테스트

- [ ] 단위 테스트 추가
- [ ] 통합 테스트 확인
- [ ] 수동 테스트 완료

## 체크리스트

- [ ] 코드 품질 검사 통과
- [ ] 문서 업데이트
- [ ] 변경사항 기록
```

### 코드 리뷰 가이드

#### 리뷰어를 위한 가이드

1. **기능성**: 코드가 의도한 대로 작동하는가?
2. **가독성**: 코드가 이해하기 쉬운가?
3. **성능**: 성능상 문제가 없는가?
4. **보안**: 보안 취약점이 없는가?
5. **테스트**: 적절한 테스트가 있는가?

#### 작성자를 위한 가이드

1. **작은 PR**: 한 번에 하나의 기능만 변경
2. **명확한 설명**: PR 설명을 상세히 작성
3. **자체 리뷰**: 제출 전 스스로 코드 검토
4. **테스트**: 변경사항에 대한 테스트 포함

## 릴리스 프로세스

### 버전 관리

프로젝트는 [Semantic Versioning](https://semver.org/)을 따릅니다:

- `MAJOR.MINOR.PATCH` (예: 1.2.3)
- `MAJOR`: 호환성이 깨지는 변경
- `MINOR`: 새 기능 추가 (하위 호환)
- `PATCH`: 버그 수정

### 릴리스 단계

1. **개발 완료**: develop 브랜치에서 기능 개발
2. **릴리스 브랜치**: `release/v1.2.3` 브랜치 생성
3. **테스트**: 전체 테스트 스위트 실행
4. **문서 업데이트**: CHANGELOG.md, 버전 번호 업데이트
5. **PR 생성**: main 브랜치로 PR
6. **태그 생성**: 릴리스 태그 생성
7. **배포**: GitHub Releases, PyPI 배포

### 릴리스 스크립트

```bash
#!/bin/bash
# scripts/release.sh

VERSION=$1
if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version>"
    exit 1
fi

# 테스트 실행
python run_tests.py ci
if [ $? -ne 0 ]; then
    echo "Tests failed"
    exit 1
fi

# 버전 업데이트
sed -i "s/version = .*/version = \"$VERSION\"/" pyproject.toml

# 커밋 및 태그
git add .
git commit -m "chore: bump version to $VERSION"
git tag "v$VERSION"

# 푸시
git push origin main
git push origin "v$VERSION"

echo "Release $VERSION completed"
```

## 개발 팁

### 효율적인 개발을 위한 팁

1. **가상환경 사용**: 의존성 충돌 방지
2. **pre-commit 훅**: 커밋 전 자동 검사
3. **IDE 설정**: 자동 포맷팅 및 린팅
4. **테스트 주도 개발**: 테스트 먼저 작성
5. **작은 커밋**: 의미 있는 단위로 커밋

### 자주 사용하는 명령어

```bash
# 개발 환경 활성화
source .venv/bin/activate

# 코드 품질 검사
python run_tests.py quality

# 테스트 실행
python run_tests.py dev

# 패키지 재설치
pip install -e . --force-reinstall

# 의존성 업데이트
pip install -r requirements-dev.txt --upgrade
```

### 문제 해결

#### 일반적인 개발 문제

1. **Import 오류**: PYTHONPATH 설정 확인
2. **테스트 실패**: 환경 변수 및 Mock 설정 확인
3. **의존성 충돌**: 가상환경 재생성
4. **성능 문제**: 프로파일링 도구 사용

## 추가 리소스

- [CI/CD 가이드](CI_CD_GUIDE.md) - GitHub Actions 워크플로우
- [코드 품질 가이드](CODE_QUALITY.md) - 품질 관리 도구
- [테스트 가이드](TESTING_GUIDE.md) - 테스트 작성 및 실행
- [아키텍처 문서](../ARCHITECTURE.md) - 시스템 설계
- [API 참조](../API_REFERENCE.md) - 함수 및 클래스 참조 