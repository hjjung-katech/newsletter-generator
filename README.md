# Newsletter Generator 프로젝트 요구사항 문서 (PRD)

## 1. 개요

* **제품명**: Newsletter Generator
* **목적**: 내부 연구원이 입력(또는 자동 추천)한 키워드를 기반으로 최신 뉴스를 수집‧요약하여 이메일로 발송하고, 필요 시 Google Drive에 저장하는 Python CLI 도구를 제공한다.
* **최종 형태**: Python 패키지 + CLI 실행 파일(추후 Docker/FastAPI 서버 모드 지원)

---

## 2. 배경 및 기회

1. 연구원들은 기술 동향‧문헌 조사를 위해 수작업으로 뉴스를 모니터링함 → 시간 소모.
2. Make.com 등 노코드 시나리오는 대량 처리·버전 관리·보안 측면에서 한계.
3. Python CLI로 재구성하면 내부망에서도 손쉽게 배포(Pipx / PyInstaller) 가능.

---

## 3. 목표(Goals)

| ID | 목표                              | 성공 지표                                                                                             |
| -- | ------------------------------- | ------------------------------------------------------------------------------------------------- |
| G1 | **CLI 한 번으로 키워드 → 이메일 발송(MVP)** | `newsletter run --keywords "ADAS,LiDAR" --to alice@corp.com` 1회 실행 ⇢ 수신자 메일함에 HTML 뉴스레터 도착 ≤ 60 초 |
| G2 | Google Drive 저장(옵션)             | 동일 실행으로 Drive HTML 업로드 성공률 ≥ 95 %                                                                 |
| G3 | 키워드 자동 추천                       | `newsletter suggest` 명령 ⇢ 추천 키워드 ≥ 10개                                                            |
| G4 | 벡터 RAG 검색 통합                    | 과거 기사 인용 ≥ 1건 포함                                                                                  |

---

## 4. 범위(Scope)

### 4.1 포함

1. **CLI 도구(Typer)**
2. 기사 수집(NewsAPI or Serper.dev or GDELT)
3. **LLM 요약·편집(Google Gemini Pro)**
4. 이메일 발송(SendGrid API 또는 Outlook Graph)
5. Google Drive 파일 업로드(선택)
6. 키워드 자동 추천(Trends API + LLM)
7. 간단한 SQLite 메타DB(기사 URL 해시, 발송 로그)

### 4.2 제외

* 외부 상용 고객 배포(내부 연구원 전용)
* 모바일 전용 앱

---

## 5. 사용자(Persona)

| 페르소나          | 설명          | 핵심 가치                           |
| ------------- | ----------- | ------------------------------- |
| Researcher R1 | R\&D 센터 연구원 | 최신 기술 뉴스 자동 요약 메일 수신으로 리서치 효율 ↑ |

---

## 6. 기능 요구사항

### 6.1 MVP (Lv‑0)

| FR-ID | 기능                  | 상세 설명                                                                        |
| ----- | ------------------- | ---------------------------------------------------------------------------- |
| FR‑01 | 키워드 기반 기사 수집        | `newsletter collect --keywords "ADAS,LiDAR"` ⇢ 최근 24 시간 기사 ≤ 20건 JSON 반환     |
| FR‑02 | 기사 요약               | Gemini Pro API로 ①30자 제목 ②300자 요약 ③키워드 3개 JSON 생성                             |
| FR‑03 | 뉴스레터 Compose        | Jinja2 템플릿으로 한국어 HTML 뉴스레터 합성                                                |
| FR‑04 | **이메일 발송**          | `newsletter send --to alice@corp.com` 또는 `newsletter run` 통합 ⇢ HTML 본문 메일 발송 |
| FR‑05 | Google Drive 저장(옵션) | `/YYYY-MM-DD/newsletter.html` 업로드                                            |

### 6.2 확장 (Lv‑1)

| FR-ID | 기능         | 상세                                                   |
| ----- | ---------- | ---------------------------------------------------- |
| FR‑06 | 키워드 자동 추천  | `newsletter suggest --domain "자율주행"` ⇢ 트렌드 키워드 ≥ 10개 |
| FR‑07 | GUI 서버(선택) | `newsletter serve` ⇢ FastAPI Swagger 폼               |

### 6.3 고도화 (Lv‑2)

| FR-ID | 기능        | 상세                           |
| ----- | --------- | ---------------------------- |
| FR‑08 | 벡터 DB RAG | 과거 기사 벡터 검색 후 관련 링크 삽입       |
| FR‑09 | 개인화 뉴스레터  | `profiles.yaml`  관심 태그 기준 필터 |

---

## 7. 비기능 요구사항(NFR)

| ID     | 항목  | 목표                            |
| ------ | --- | ----------------------------- |
| NFR‑01 | 성능  | 20개 기사 처리 & 메일 발송 < 60 초      |
| NFR‑02 | 보안  | API 키 .env 관리, 내부 SMTP 연동 TLS |
| NFR‑03 | 테스트 | pytest 커버리지 ≥ 80 %            |

---

## 8. 시스템 아키텍처

```mermaid
flowchart TD
    subgraph CLI
        A1[topics.yaml]
        A2[newsletter run]
    end
    subgraph Core
        C1[collect.py]\nREST Crawlers
        C2[summarize.py]\nGemini Pro
        C3[compose.py]\nJinja2
        C4[deliver.py]\nEmail / Drive
    end
    subgraph Storage
        S1[raw JSON]
        S2[SQLite meta]
        S3[Chroma (Lv‑2)]
    end

    A2-->C1-->S1
    C1-->C2-->S1
    C2-->C3
    C3-->C4
    C4-->S2
    S1-->S3
```

---

## 9. 기술 스택 & 라이브러리

| 영역  | 라이브러리                                | 이유                    |
| --- | ------------------------------------ | --------------------- |
| CLI | Typer                                | click 기반, 자동 --help   |
| LLM | **google‑generativeai (Gemini Pro)** | 한국어 성능, 내부 연구 라이선스    |
| 크롤링 | NewsAPI, Serper.dev, GDELT           | 백업용 다중 소스             |
| 이메일 | SendGrid / Outlook Graph             | 대량 발송 & 내부 SMTP 대체 가능 |
| 포맷  | Jinja2 + Tailwind CDN                | 빠른 스타일링               |
| 배포  | PyPI + pipx / PyInstaller --onefile  | 내부 연구원 설치 편의          |

---

## 10. 마일스톤 & 일정(예시)

| Phase              | 기간       | 완료 기준                    |
| ------------------ | -------- | ------------------------ |
| M0 Kick‑off        | T0 + 0주  | PRD 승인                   |
| **M1 MVP(이메일 발송)** | T0 + 4주  | FR‑01 \~ FR‑05 통합 테스트 통과 |
| M2 Lv‑1 확장         | T0 + 8주  | 키워드 추천·GUI 데모            |
| M3 Lv‑2 RAG        | T0 + 12주 | 과거 기사 인용 발송 성공           |
| M4 내부 정식 배포        | T0 + 14주 | PyPI 사내 레포 버전 1.0 릴리스    |

---

## 11. 성공 지표(KPI)

1. 내부 연구원 주간 활성 사용자(WAU) ≥ 20명
2. 수작업 대비 뉴스 수집·편집 시간 80 % 절감
3. 사내 메일 오픈율 ≥ 50 %

---

## 12. 리스크 & 완화 전략

| 리스크          | 영향    | 완화                                 |
| ------------ | ----- | ---------------------------------- |
| 뉴스 API 쿼터 초과 | 수집 실패 | GDELT fallback, 캐시                 |
| LLM 비용 증가    | 운영비 ↑ | Gemini Pro 토큰 분석 → 요약 단계 chunk 최적화 |
| 사내 메일 스팸     | 발송 실패 | 내부 SMTP 허용 목록 등록                   |

---

## 13. 향후 발전 방향

* Notion DB 자동 싱크
* Slack 봇 알림
* PDF 뉴스레터 디자인 템플릿

---

### 문서 버전 기록

| 버전  | 일자         | 작성자     | 변경 요약                                           |
| --- | ---------- | ------- | ----------------------------------------------- |
| 0.2 | 2025‑05‑09 | ChatGPT | MVP 범위 이메일 발송 반영, LLM → Gemini Pro, 대상 → 내부 연구원 |
| 0.1 | 2025‑05‑09 | ChatGPT | 초기 초안                                           |
