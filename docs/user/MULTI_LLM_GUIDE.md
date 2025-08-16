# Multi-LLM 설정 가이드

Newsletter Generator는 이제 여러 LLM 제공자를 지원하며, 기능별로 다른 모델을 사용할 수 있습니다.

## 🤖 지원되는 LLM 제공자

### Google Gemini (기본)
- **모델**: `gemini-1.5-pro`, `gemini-2.5-pro`, `gemini-pro`
- **강점**: 무료 할당량 제공, 긴 컨텍스트 지원
- **API 키**: `GEMINI_API_KEY`

### OpenAI GPT
- **모델**: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-3.5-turbo`
- **강점**: 뛰어난 텍스트 생성 품질, 빠른 응답
- **API 키**: `OPENAI_API_KEY`

### Anthropic Claude
- **모델**: `claude-3-5-sonnet-20241022`, `claude-3-sonnet-20240229`, `claude-3-haiku-20240307`
- **강점**: 안전성, 긴 컨텍스트, 정확한 분석
- **API 키**: `ANTHROPIC_API_KEY`

## ⚙️ 설정 방법

### 1. 환경 변수 설정

`.env` 파일에 사용할 제공자의 API 키를 추가하세요:

```bash
# 기본 제공자 (필수)
GEMINI_API_KEY=your_gemini_api_key_here

# 추가 제공자 (선택)
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# 비용 추적 디버깅 (선택)
DEBUG_COST_TRACKING=true
```

### 2. config.yml 설정

`config.yml` 파일의 `llm_settings` 섹션에서 세밀한 LLM 설정을 할 수 있습니다:

```yaml
llm_settings:
  # 기본 제공자
  default_provider: gemini

  # 제공자별 API 키 (환경 변수로 설정하는 것을 권장)
  api_keys:
    gemini: ${GEMINI_API_KEY}
    openai: ${OPENAI_API_KEY}
    anthropic: ${ANTHROPIC_API_KEY}

  # 제공자별 모델 설정
  provider_models:
    gemini:
      fast: gemini-1.5-pro
      standard: gemini-2.5-pro
      advanced: gemini-2.5-pro
    openai:
      fast: gpt-4o-mini
      standard: gpt-4o
      advanced: gpt-4o
    anthropic:
      fast: claude-3-haiku-20240307
      standard: claude-3-sonnet-20240229
      advanced: claude-3-5-sonnet-20241022

  # 기능별 LLM 모델 설정
  models:
    keyword_generation:
      provider: openai
      model: gpt-4o-mini
      temperature: 0.7
      max_retries: 3
      timeout: 30

    theme_extraction:
      provider: anthropic
      model: claude-3-haiku-20240307
      temperature: 0.3
      max_retries: 2
      timeout: 60

    news_summarization:
      provider: gemini
      model: gemini-2.5-pro
      temperature: 0.3
      max_retries: 3
      timeout: 120

    section_regeneration:
      provider: anthropic
      model: claude-3-sonnet-20240229
      temperature: 0.5
      max_retries: 2
      timeout: 90

    introduction_generation:
      provider: openai
      model: gpt-4o
      temperature: 0.6
      max_retries: 2
      timeout: 60

    html_generation:
      provider: gemini
      model: gemini-1.5-pro
      temperature: 0.2
      max_retries: 2
      timeout: 90
```

## 🎯 기능별 LLM 용도

### 키워드 생성 (keyword_generation)
- **추천 모델**: OpenAI GPT-4o-mini, Gemini 1.5 Pro
- **이유**: 창의적 사고와 키워드 발굴에 강함

### 주제 추출 (theme_extraction)
- **추천 모델**: Claude 3 Haiku, Gemini 1.5 Pro
- **이유**: 빠르고 정확한 분류 작업에 적합

### 뉴스 요약 (news_summarization)
- **추천 모델**: Gemini 2.5 Pro, Claude 3.5 Sonnet
- **이유**: 긴 텍스트 처리와 정확한 요약에 강함

### 섹션 재생성 (section_regeneration)
- **추천 모델**: Claude 3 Sonnet, GPT-4o
- **이유**: 컨텍스트 이해와 일관성 있는 텍스트 생성

### 도입부 생성 (introduction_generation)
- **추천 모델**: GPT-4o, Claude 3.5 Sonnet
- **이유**: 매력적이고 자연스러운 텍스트 작성

### HTML 생성 (html_generation)
- **추천 모델**: Gemini 1.5 Pro, GPT-4o
- **이유**: 구조화된 출력과 포맷팅에 강함

## 💰 비용 최적화 전략

### 1. 계층별 모델 사용

```yaml
# 비용 효율적인 설정 예시
llm_settings:
  models:
    # 간단한 작업은 저렴한 모델 사용
    keyword_generation:
      provider: openai
      model: gpt-4o-mini  # $0.15/1M tokens (input)

    theme_extraction:
      provider: anthropic
      model: claude-3-haiku-20240307  # $0.25/1M tokens (input)

    # 복잡한 작업은 고성능 모델 사용
    news_summarization:
      provider: gemini
      model: gemini-2.5-pro  # $0.7/1K tokens (input)

    html_generation:
      provider: openai
      model: gpt-4o  # $5.00/1M tokens (input)
```

### 2. 제공자별 비용 비교 (2025년 5월 기준)

| 제공자 | 모델 | Input (1M tokens) | Output (1M tokens) |
|--------|------|------------------|-------------------|
| **Gemini** | 2.5 Pro | $0.70 | $1.40 |
| **OpenAI** | GPT-4o | $5.00 | $15.00 |
| **OpenAI** | GPT-4o-mini | $0.15 | $0.60 |
| **Anthropic** | Claude 3.5 Sonnet | $3.00 | $15.00 |
| **Anthropic** | Claude 3 Haiku | $0.25 | $1.25 |

## 🔧 사용 방법

### CLI에서 제공자 정보 확인

```bash
# 사용 가능한 LLM 제공자 목록 확인
newsletter list-providers
```

출력 예시:
```
=== Available LLM Providers ===

✅ gemini (Available)
   - fast: gemini-1.5-pro
   - standard: gemini-2.5-pro
   - advanced: gemini-2.5-pro

✅ openai (Available)
   - fast: gpt-4o-mini
   - standard: gpt-4o
   - advanced: gpt-4o

❌ anthropic (Not Available - API key not set)
   - fast: claude-3-haiku-20240307
   - standard: claude-3-sonnet-20240229
   - advanced: claude-3-5-sonnet-20241022

=== Current Task Assignments ===

• keyword_generation → openai (gpt-4o-mini)
• theme_extraction → gemini (gemini-1.5-pro) [fallback]
• news_summarization → gemini (gemini-2.5-pro)
• section_regeneration → gemini (gemini-1.5-pro) [fallback]
• introduction_generation → openai (gpt-4o)
• html_generation → gemini (gemini-1.5-pro)
```

### 프로그래밍 방식 사용

```python
from newsletter.llm_factory import get_llm_for_task, get_available_providers

# 특정 작업용 LLM 가져오기
summarization_llm = get_llm_for_task("news_summarization")

# 사용 가능한 제공자 확인
available = get_available_providers()
print(f"Available providers: {available}")

# 제공자 정보 가져오기
from newsletter.llm_factory import get_provider_info
info = get_provider_info()
```

## 🔄 Fallback 시스템

시스템은 자동 fallback을 지원합니다:

1. **설정된 제공자가 사용 불가능한 경우** (API 키 없음, 모듈 없음)
2. **사용 가능한 다른 제공자를 자동 선택**
3. **콘솔에 경고 메시지 출력**

```bash
Warning: anthropic not available, falling back to gemini
```

## 📊 비용 추적

### 자동 비용 추적

모든 LLM 호출은 자동으로 비용이 추적됩니다:

```python
# 비용 추적 활성화 (환경 변수)
DEBUG_COST_TRACKING=true

# 실행 시 비용 정보가 출력됩니다
[Token Usage - gpt-4o] Input: 1250, Output: 340, Cost: $0.011100
[Token Usage - claude-3-sonnet] Input: 890, Output: 230, Cost: $0.006120
[Token Usage - gemini-2.5-pro] Input: 2100, Output: 560, Cost: $0.002254
```

### 제공자별 비용 콜백

```python
from newsletter.cost_tracking import get_cost_callback_for_provider

# 제공자별 비용 추적 콜백 생성
gemini_callback = get_cost_callback_for_provider("gemini")
openai_callback = get_cost_callback_for_provider("openai")
anthropic_callback = get_cost_callback_for_provider("anthropic")

# 나중에 비용 요약 확인
summary = gemini_callback.get_summary()
print(f"Total cost: ${summary['total_cost_usd']:.6f}")
```

## 🚨 문제 해결

### 1. "Provider not available" 오류

```bash
# API 키 확인
echo $GEMINI_API_KEY
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY

# 의존성 설치 확인
pip install langchain-google-genai langchain-openai langchain-anthropic
```

### 2. 비용 추적이 작동하지 않는 경우

```bash
# 디버그 모드 활성화
export DEBUG_COST_TRACKING=true

# 로그 확인
newsletter run --keywords "test" --output-format html
```

### 3. Fallback이 예상대로 작동하지 않는 경우

```bash
# 제공자 상태 확인
newsletter list-providers

# config.yml 설정 검증
python -c "from newsletter.config import LLM_CONFIG; print(LLM_CONFIG)"
```

## 🔮 향후 계획

- **Azure OpenAI** 지원 추가
- **로컬 LLM** (Ollama) 지원
- **배치 처리** 최적화
- **비용 예산** 제한 기능
- **A/B 테스팅** 프레임워크

## 📚 관련 문서

- [CLI 참조](CLI_REFERENCE.md)
- [설치 가이드](../setup/INSTALLATION.md)
- [개발자 가이드](../dev/DEVELOPMENT_GUIDE.md)
- [아키텍처 문서](../ARCHITECTURE.md)
