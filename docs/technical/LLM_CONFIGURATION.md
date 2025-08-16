# LLM 설정 가이드

Newsletter Generator는 다양한 LLM 제공자를 지원하여 각 기능에 최적화된 모델을 사용할 수 있습니다.

## 지원하는 LLM 제공자

### 1. Google Gemini
- **gemini-2.5-pro-preview-03-25**: 최신 고성능 모델
- **gemini-2.5-flash-preview-05-20**: 빠른 응답의 최신 모델
- **gemini-1.5-pro**: 안정적인 표준 모델
- **gemini-1.5-flash-latest**: 빠른 응답 모델

### 2. Anthropic Claude
- **claude-sonnet-4-20250514**: 최신 Claude 4 모델
- **claude-3-7-sonnet-latest**: Claude 3.7 최신 모델
- **claude-3-5-haiku-latest**: 빠른 응답용 모델

### 3. OpenAI (선택사항)
- **gpt-4o**: 표준 GPT-4 모델
- **gpt-4o-mini**: 경량화된 GPT-4 모델

## 환경변수 설정

`.env` 파일에 다음 API 키들을 설정하세요:

```bash
# 필수 API 키
GEMINI_API_KEY=your_gemini_api_key_here

# 선택적 API 키
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

## 기능별 LLM 모델 설정

`config.yml` 파일에서 각 기능별로 최적화된 LLM 모델을 설정할 수 있습니다:

### 현재 설정

```yaml
llm_settings:
  default_provider: "gemini"

  models:
    # 키워드 생성 - 창의성이 중요하므로 Claude 사용
    keyword_generation:
      provider: "anthropic"
      model: "claude-3-7-sonnet-latest"
      temperature: 0.7
      max_retries: 2
      timeout: 60

    # 테마 추출 - 빠른 분석을 위해 Flash 모델 사용
    theme_extraction:
      provider: "gemini"
      model: "gemini-2.5-flash-preview-05-20"
      temperature: 0.2
      max_retries: 2
      timeout: 60

    # 뉴스 요약 - 정확성을 위해 최신 Gemini Pro 사용
    news_summarization:
      provider: "gemini"
      model: "gemini-2.5-pro-preview-03-25"
      temperature: 0.3
      max_retries: 3
      timeout: 120

    # 섹션 재생성 - 구조화된 작업을 위해 Claude 사용
    section_regeneration:
      provider: "anthropic"
      model: "claude-3-7-sonnet-latest"
      temperature: 0.3
      max_retries: 2
      timeout: 120

    # 뉴스레터 소개 생성 - 자연스러운 글쓰기를 위해 Claude 사용
    introduction_generation:
      provider: "anthropic"
      model: "claude-3-7-sonnet-latest"
      temperature: 0.4
      max_retries: 2
      timeout: 60

    # HTML 생성 - 복잡한 구조화 작업을 위해 Gemini Pro 사용
    html_generation:
      provider: "gemini"
      model: "gemini-2.5-pro-preview-03-25"
      temperature: 0.2
      max_retries: 3
      timeout: 180

    # 기사 점수 매기기 - 빠른 판단을 위해 Flash 모델 사용
    article_scoring:
      provider: "gemini"
      model: "gemini-2.5-flash-preview-05-20"
      temperature: 0.1
      max_retries: 2
      timeout: 30

    # 번역 작업 - 정확성을 위해 Gemini Pro 사용
    translation:
      provider: "gemini"
      model: "gemini-2.5-pro-preview-03-25"
      temperature: 0.1
      max_retries: 2
      timeout: 60
```

## 매개변수 설명

### provider
- 사용할 LLM 제공자 (`gemini`, `anthropic`, `openai`)

### model
- 사용할 구체적인 모델명

### temperature
- 응답의 창의성 조절 (0.0 = 결정적, 1.0 = 창의적)
- 키워드 생성: 0.7 (창의적)
- 정확한 요약/번역: 0.1-0.3 (결정적)

### max_retries
- API 호출 실패 시 재시도 횟수

### timeout
- API 호출 타임아웃 (초)

## 제공자별 모델 티어

```yaml
provider_models:
  gemini:
    fast: "gemini-2.5-flash-preview-05-20"
    standard: "gemini-1.5-pro"
    advanced: "gemini-2.5-pro-preview-03-25"

  anthropic:
    fast: "claude-3-5-haiku-latest"
    standard: "claude-3-7-sonnet-latest"
    advanced: "claude-sonnet-4-20250514"

  openai:
    fast: "gpt-4o-mini"
    standard: "gpt-4o"
    advanced: "gpt-4o"
```

## Fallback 메커니즘

설정된 LLM 제공자가 사용할 수 없는 경우, 시스템은 자동으로 사용 가능한 다른 제공자로 전환합니다:

1. 설정된 제공자 확인
2. API 키 및 라이브러리 사용 가능 여부 확인
3. 사용 불가능한 경우 사용 가능한 다른 제공자로 자동 전환
4. 모든 제공자가 사용 불가능한 경우 오류 발생

## 비용 최적화 팁

### 1. 작업 특성에 맞는 모델 선택
- **빠른 응답이 필요한 작업**: Flash/Haiku 모델 사용
- **높은 정확성이 필요한 작업**: Pro/Sonnet 모델 사용
- **창의적 작업**: 높은 temperature 설정

### 2. 제공자별 장단점 활용
- **Gemini**: 한국어 지원이 우수, 빠른 응답
- **Claude**: 자연스러운 글쓰기, 구조화된 작업에 강함
- **OpenAI**: 안정적이지만 비용이 높음

### 3. Temperature 최적화
- 정확한 요약/번역: 0.1-0.2
- 일반적인 텍스트 생성: 0.3-0.4
- 창의적 콘텐츠 생성: 0.6-0.8

## 테스트 및 검증

LLM 설정을 테스트하려면 다음 명령을 실행하세요:

```bash
# 기본 LLM 시스템 테스트
python test_llm.py

# 상세한 제공자별 테스트
python test_llm_providers.py
```

## 문제 해결

### 1. API 키 오류
```
Warning: GEMINI_API_KEY not found in .env file
```
- `.env` 파일에 올바른 API 키가 설정되어 있는지 확인
- API 키가 유효한지 확인

### 2. 모델 없음 오류
```
Error code: 404 - model not found
```
- 모델명이 올바른지 확인
- 해당 제공자에서 모델이 사용 가능한지 확인
- 최신 모델명으로 업데이트

### 3. 라이브러리 없음 오류
```
ImportError: langchain_anthropic is not installed
```
- 필요한 라이브러리 설치:
```bash
pip install langchain-anthropic
pip install langchain-openai
```

### 4. 권한 오류
- API 키의 권한이 올바른지 확인
- 계정의 사용 한도를 확인

## 고급 설정

### 커스텀 LLM 제공자 추가

새로운 LLM 제공자를 추가하려면:

1. `newsletter/llm_factory.py`에서 새 Provider 클래스 구현
2. `LLMFactory`의 `providers` 딕셔너리에 추가
3. `config.yml`에 새 제공자 설정 추가

### 모델별 세부 조정

각 모델의 성능을 최적화하려면:

1. Temperature 값 조정
2. Max retries 및 timeout 값 최적화
3. 프롬프트 엔지니어링 적용
4. 비용 vs 품질 트레이드오프 고려

이 설정을 통해 Newsletter Generator는 각 작업에 가장 적합한 LLM을 자동으로 선택하여 최상의 결과를 제공합니다.
