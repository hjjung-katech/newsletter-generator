# Multi-LLM 사용자 가이드

이 문서는 사용자 관점의 빠른 설정/운영 포인트를 제공합니다.
세부 모델 매핑과 파라미터 계약은 기술 정본 문서(`../technical/LLM_CONFIGURATION.md`)를 기준으로 합니다.

## 지원 제공자

- Google Gemini
- OpenAI
- Anthropic Claude

## 빠른 설정

`.env`에 최소 1개 이상의 LLM API 키를 설정하세요.

```bash
# 최소 1개 이상 필요
GEMINI_API_KEY=...
# OPENAI_API_KEY=...
# ANTHROPIC_API_KEY=...
```

뉴스 수집에는 `SERPER_API_KEY`가 필요합니다.

## 동작 원칙

- 기능별로 다른 모델이 할당될 수 있습니다.
- 설정된 제공자를 사용할 수 없으면 사용 가능한 제공자로 fallback합니다.
- 비용/응답 품질은 모델별 설정에 따라 달라집니다.

## 운영 체크리스트

1. API 키 누락 여부 확인
2. `newsletter list-providers`로 사용 가능 제공자 확인
3. 실패 시 fallback 로그 확인

## 자주 보는 문제

- `model not found`: 모델명/권한 확인
- `API key not found`: `.env` 누락 확인
- `timeout`: 해당 task의 timeout/retry 값 점검

## 정본 문서

- 기술 정본(모델/파라미터): `../technical/LLM_CONFIGURATION.md`
- 환경변수 정본: `../reference/environment-variables.md`
- 설치/실행: `../setup/INSTALLATION.md`, `../setup/QUICK_START_GUIDE.md`
