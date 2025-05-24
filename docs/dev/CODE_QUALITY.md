# 코드 품질 관리 가이드

이 문서는 Newsletter Generator 프로젝트의 코드 품질을 관리하는 방법에 대한 가이드입니다.

## 코드 포맷팅

모든 Python 코드는 [Black](https://black.readthedocs.io/en/stable/) 포맷터를 사용하여 포맷팅됩니다. 
Black은 PEP 8을 준수하며, 일관된 코드 스타일을 강제합니다.

로컬에서 코드 포맷팅을 실행하려면:
```bash
black newsletter
black tests
```

## 테스트

모든 기능에 대한 테스트는 `tests/` 디렉토리에 작성됩니다. 테스트는 [pytest](https://docs.pytest.org/) 프레임워크를 사용합니다.

로컬에서 테스트를 실행하려면:
```bash
python -m pytest tests/ --ignore=tests/_backup
```

## 코드 커버리지

코드 커버리지는 pytest-cov 플러그인을 사용하여 측정됩니다. 
현재 목표는 50% 이상의 코드 커버리지를 유지하는 것입니다.

로컬에서 커버리지를 확인하려면:
```bash
python -m pytest tests/ --cov=newsletter --ignore=tests/_backup
```

HTML 형식의 상세 커버리지 보고서를 생성하려면:
```bash
python -m pytest tests/ --cov=newsletter --cov-report=html --ignore=tests/_backup
```

생성된 보고서는 `htmlcov/` 디렉토리에서 확인할 수 있습니다.

## 커버리지 향상 방법

현재 낮은 커버리지를 보이는 모듈은 다음과 같습니다:
- `cli.py` (13%)
- `deliver.py` (15%)
- `graph.py` (28%)
- `tools.py` (47%)

이 모듈들에 대한 테스트를 추가하여 커버리지를 향상시킬 수 있습니다.

### 우선순위가 높은 영역:

1. **graph.py**: 뉴스레터 생성 워크플로우의 핵심 로직을 포함
2. **tools.py**: 다양한 유틸리티 함수들의 모음으로, 여러 모듈에서 사용됨

## CI/CD 통합

GitHub Actions를 통해 모든 PR과 main 브랜치에 대한 푸시에서 자동으로 코드 품질 검사가 실행됩니다.

워크플로우는 다음을 확인합니다:
1. Black 포맷팅 준수
2. 모든 테스트 통과
3. 코드 커버리지 50% 이상 유지

## 기타 코드 품질 향상 방안

1. **정적 코드 분석 도구 도입**: 
   - flake8, pylint 등의 도구를 도입하여 정적 코드 분석을 수행
   
2. **타입 힌팅 도입**:
   - mypy를 사용하여 타입 검사 수행
   
3. **문서화 향상**:
   - 각 모듈과 함수에 대한 문서화 추가
   - API 문서 자동 생성 도구(Sphinx 등) 도입

## 백업 테스트 관리

`tests/_backup/` 디렉토리의 테스트는 이전 버전의 코드를 위한 것이거나 더 이상 사용되지 않는 테스트입니다.
이 테스트들은 CI/CD 파이프라인에서 실행되지 않으며, 참조 목적으로만 유지됩니다. 