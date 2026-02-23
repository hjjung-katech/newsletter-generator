# LangSmith 연동 및 비용 추적 가이드

이 문서는 뉴스레터 생성기에서 LangSmith 연동 및 Google Generative AI 비용 추적을 설정하는 방법을 안내합니다.

## `.env` 파일을 사용한 환경 변수 설정

LangSmith 및 기타 API 키를 안전하게 관리하기 위해 프로젝트 루트 디렉토리에 `.env` 파일을 사용하는 것을 권장합니다.

1.  **`.env.example` 파일 복사**: 프로젝트 루트에 있는 `.env.example` 파일을 `.env` 파일로 복사합니다.
    ```bash
    cp .env.example .env
    ```
2.  **`.env` 파일 수정**: `.env` 파일을 열어 실제 API 키와 설정을 입력합니다.

    ```dotenv
    # .env 파일 예시
    SERPER_API_KEY="YOUR_SERPER_API_KEY"
    GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    # GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/google_credentials.json"

    # LangSmith Configuration
    LANGCHAIN_TRACING_V2="true"
    LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
    LANGCHAIN_API_KEY="YOUR_LANGSMITH_API_KEY" # 실제 LangSmith API 키로 변경
    LANGCHAIN_PROJECT="newsletter-generator-tracing-langchain" # 원하는 프로젝트 이름으로 변경 가능
    ENABLE_COST_TRACKING="true"  # Google Generative AI 비용 추적 활성화

    # (기타 필요한 설정)
    ```

    **주요 환경 변수:**
    *   `LANGCHAIN_TRACING_V2="true"`: LangSmith 트레이싱을 활성화합니다.
    *   `LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"`: LangSmith API 엔드포인트입니다. (일반적으로 변경 불필요)
    *   `LANGCHAIN_API_KEY="<YOUR_API_KEY>"`: **필수!** LangSmith 웹사이트에서 발급받은 API 키를 입력합니다.
    *   `LANGCHAIN_PROJECT="<YOUR_PROJECT_NAME>"`: LangSmith 프로젝트 이름을 지정합니다. (예: `newsletter-generator-dev`)
    *   `ENABLE_COST_TRACKING="true"`: `GoogleGenAICostCB`를 이용한 비용 추적을 활성화합니다.
    *   `GEMINI_API_KEY="<YOUR_GEMINI_API_KEY>"`: **필수!** Google AI Studio에서 발급받은 Gemini API 키를 입력합니다.

    **참고:** `.env` 파일은 민감한 정보를 포함하므로, `.gitignore` 파일에 추가하여 Git 저장소에 포함되지 않도록 해야 합니다. (이미 `.gitignore`에 `*.env` 또는 `.env`가 포함되어 있을 수 있습니다.)

### 기존 방식 (셸 환경 변수 직접 설정 - 권장하지 않음)

기존처럼 셸에서 직접 환경 변수를 설정할 수도 있지만, `.env` 파일을 사용하는 것이 더 안전하고 편리합니다.

```bash
# Windows PowerShell
# $Env:LANGCHAIN_TRACING_V2 = "true"
# ... (이하 생략)

# Linux/macOS
# export LANGCHAIN_TRACING_V2=true
# ... (이하 생략)
```

### 비용 추적만 활성화하려면 (`.env` 파일 사용)

```dotenv
# .env 파일 내 설정
ENABLE_COST_TRACKING="true"
```

### 명령줄에서 비용 추적 활성화

`--track-cost` 플래그를 사용하여 뉴스레터 생성 시 비용 추적을 활성화할 수 있습니다:

```bash
newsletter run --domain "인공지능" --track-cost
```

## 오류 해결

### LangSmith 트레이싱 오류

LangChain 0.3+ 버전에서는 다음과 같은 오류가 나타날 수 있습니다:

```
Warning: Failed to initialize LangSmith tracing: 'Client' object has no attribute 'get_tracing_callback'
```

이 오류는 LangChain 0.3+ 버전에서 LangSmith 클라이언트 API가 변경되었기 때문에 발생합니다. 최신 버전에서는 `LangChainTracer`를 직접 생성하여 사용해야 합니다.

### Google Generative AI 매개변수 오류

다음 경고가 표시되는 경우:

```
Unexpected argument 'request_timeout' provided to ChatGoogleGenerativeAI. Did you mean: 'timeout'?
Unexpected argument 'streaming' provided to ChatGoogleGenerativeAI. Did you mean: 'disable_streaming'?
```

API 매개변수 이름이 변경되었습니다:
- `request_timeout` → `timeout`
- `streaming=True` → `disable_streaming=False`

## 요청 시간 초과 및 재시도 설정

Google Generative AI API 호출이 무한 대기 상태에 빠지는 것을 방지하기 위해 다음과 같은 매개변수를 설정했습니다:

```python
ChatGoogleGenerativeAI(
    model="gemini-1.5-pro-latest",
    google_api_key=config.GEMINI_API_KEY,
    temperature=0.3,
    request_timeout=60,  # 60초 타임아웃 설정
    max_retries=2,       # 최대 2회 재시도
    streaming=True,      # 응답 스트리밍으로 블로킹 방지
)
```

## 비용 계산 방식

현재(2025년 5월 기준) Gemini 2.5 Pro 모델의 비용은 다음과 같습니다:

- 입력 토큰: $0.0007 / 1K 토큰
- 출력 토큰: $0.0014 / 1K 토큰

가격은 변경될 수 있으므로 정확한 정보는 [Google AI Studio 가격 페이지](https://ai.google.dev/pricing)에서 확인하세요.

## 문제 해결

### 트레이싱이 작동하지 않는 경우

1.  `.env` 파일에 `LANGCHAIN_API_KEY`가 올바르게 설정되었는지 확인하세요.
2.  `LANGCHAIN_TRACING_V2`가 `"true"`로 설정되어 있는지 확인하세요.
3.  최신 버전의 langsmith 및 langchain 라이브러리를 사용하고 있는지 확인하세요:
   ```bash
   pip install -U langsmith langchain-core langchain langchain-google-genai
   ```

4. LangSmith 계정에 로그인하여 API 키가 유효한지 확인하세요.
5. 인터넷 연결을 확인하고 네트워크 방화벽이 api.smith.langchain.com에 접근할 수 있는지 확인하세요.
6. `newsletter/config.py` 파일에서 `load_dotenv()`가 호출되어 `.env` 파일이 제대로 로드되는지 확인하세요.

### 비용 추적이 작동하지 않는 경우

1.  `--track-cost` 옵션이 명령줄에 포함되어 있거나, `.env` 파일에 `ENABLE_COST_TRACKING="true"`가 설정되어 있는지 확인하세요.
2.  `GoogleGenAICostCB` 콜백이 LLM 초기화에 포함되어 있는지 확인하세요.
3.  `.env` 파일에 `DEBUG_COST_TRACKING="1"` 환경 변수를 설정하여 상세 로그를 확인할 수 있습니다.
