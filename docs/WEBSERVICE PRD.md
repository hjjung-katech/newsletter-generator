# 📄 프로젝트 요구사항 문서 (PRD)

> **프로젝트명:** Newsletter Generator Web Service on Railway
> **저장소:** [https://github.com/hjjung-katech/newsletter-generator](https://github.com/hjjung-katech/newsletter-generator)
> **작성일:** 2025-05-30
> **수정일:** 2025-05-30 (v1.1 – 예약 발송/관리 기능 추가)
> **작성자:** *Your Name*

---

## 1. 프로젝트 개요

| 항목         | 설명                                                                                                          |
| ---------- | ----------------------------------------------------------------------------------------------------------- |
| **목적**     | 기존 CLI 기반 *newsletter-generator*를 웹 서비스로 확장하여 비개발자도 키워드(또는 도메인)만 입력하면 뉴스 요약·구성·메일 발송까지 원‑스톱으로 사용할 수 있도록 한다. |
| **범위**     | 백엔드(Flask), 간단한 프론트엔드(HTML + Fetch API), Railway PaaS 배포, 영구 스토리지(SQLite) 구성, **정기 예약 발송 및 예약 현황 관리** 포함.   |
| **대상 사용자** | 연구원, PM, 일반 직원 등 정기적으로 주제별 트렌드 뉴스를 받아보고 싶은 내·외부 사용자.                                                        |
| **핵심 가치**  | *"CLI의 강력함 + 웹의 접근성"* — 설치 없이 Browser‑Only 사용, 히스토리 및 예약 발송 지원.                                             |

---

## 2. 목표

### 2.1 기능적 목표 (MVP‑Plus)

1. **키워드/도메인 기반 뉴스 수집** — `newsletter run` & `newsletter suggest` 래핑
2. **요약 & 본문 생성** — 기존 `collect.py`, `summarize.py`, `compose.py` 재사용
3. **HTML 미리보기 & 다운로드**
4. **즉시 이메일 발송**
5. **정기 예약 발송** — 사용자가 *매주 월·수·금 09:00* 등 규칙을 지정
6. **예약 현황 조회·취소** — 활성/만료 예약 목록 UI 제공
7. **사용 히스토리 관리** (최근 20개)

### 2.2 비기능적 목표

* **배포 편의** : Railway 1‑Click Deploy, Nixpacks 빌드
* **반응 속도** : 요청‑응답 5초 이내(요약 지연 시 프로그레스바/폴링)
* **보안** : API Key 는 Railway env vars 관리, CSRF disabled but JWT admin auth
* **가용성** : Hobby 플랜 SLA 내(99.9% 미만 허용)

---

## 3. 현행 시스템 분석

(동일 – 생략)

---

## 4. 요구 기능 상세

| ID       | 기능           | 설명                                   | 우선순위 |
| -------- | ------------ | ------------------------------------ | ---- |
| F‑01     | 키워드 검색       | 키워드 배열 입력 → 뉴스 수집 → 요약 → HTML 제공     | ★★★  |
| F‑02     | 도메인 추천       | 도메인 문자열 입력 → 관련 키워드 추천 → F‑01 실행     | ★★☆  |
| F‑03     | 즉시 이메일 발송    | SendGrid API 활용, HTML 본문 or 첨부       | ★★★  |
| F‑04     | 히스토리 조회      | 최근 요청/결과 저장, 목록/재사용                  | ★★☆  |
| **F‑05** | **정기 예약 발송** | RRULE(ISO8601) 기반 스케줄 등록·저장·백그라운드 실행 | ★★☆  |
| **F‑06** | **예약 현황 관리** | 활성/만료 예약 목록 조회, 개별 취소, 즉시 실행         | ★★☆  |

> ✨ **MVP‑Plus = F‑01 \~ F‑05**
> F‑06은 예약 기능 UI와 함께 동일 스프린트 내 개발 권장.

---

## 5. 시스템 아키텍처 (업데이트)

```mermaid
flowchart LR
    Browser-->(HTTPS)FlaskAPI[Flask Backend]
    Browser-->|WebSocket/Polling|Progress[Status Endpoint]
    FlaskAPI-->|invoke|CLI[newsletter modules]
    FlaskAPI-->|enqueue|Queue[(Redis‑RQ)]
    Worker[Background Worker]-->|run|CLI
    subgraph Railway
      FlaskAPI
      Worker
      SQLite[(storage.db)]
      Redis[(redis)]
    end
```

* **정기 예약 발송** : Redis‑RQ + Railway Cron (kick every 15 min) → Worker pull RRULE schedule.
* **예약 현황** : `schedules` 테이블 + endpoint `/api/schedules`.

---

## 6. 기술 스택 (변경 사항만)

| 레이어   | 추가 기술            | 이유                    |
| ----- | ---------------- | --------------------- |
| Queue | Redis‑RQ         | 예약 잡 실행/재시도           |
| Front | Alpine.js + HTMX | 예약 목록 실시간 갱신에 간결하게 사용 |

---

## 7. 데이터 모델 (SQLite – 확장)

```sql
CREATE TABLE schedules (
  id TEXT PRIMARY KEY,
  params JSON NOT NULL,
  rrule TEXT NOT NULL,           -- iCal RRULE
  next_run TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  enabled INTEGER DEFAULT 1      -- 1 = active
);
```

---

## 8. API 설계 (추가)

### 8.1 POST `/api/schedule`

| 파라미터     | 타입         | 필수  | 설명                                                      |
| -------- | ---------- | --- | ------------------------------------------------------- |
| keywords | list\[str] | 조건부 |                                                         |
| domain   | str        | 조건부 |                                                         |
| rrule    | str        | ✅   | ISO8601 RRULE (e.g. `FREQ=WEEKLY;BYDAY=MO,TH;BYHOUR=9`) |
| email    | str        | ✅   | 수신 이메일                                                  |

**응답** `201 Created`

```json
{ "status": "scheduled", "schedule_id": "abc123" }
```

### 8.2 GET `/api/schedules`

반환: 활성 예약 배열.

### 8.3 DELETE `/api/schedule/{id}`

개별 예약 취소.

---

## 9. UI/UX 변경 포인트

* 메인 대시보드에 **"정기 발송 예약"** 탭 추가 (예시 HTML mockup 이미지 참조).
* 좌측 사이드바 또는 상단 탭으로 **"히스토리"** 와 **"예약 관리"** 구분.
* 예약 카드: 주기 / 다음 실행 시각 / 상태(활성, 일시정지) / 액션(**취소**, **즉시 실행**).
* **예시 뉴스레터 이미지** : `/static/img/newsletter_sample.png` 포함, 예약 생성 완료 안내 화면에 썸네일 표시.

---

## 10. 일정 (업데이트)

| 단계          | 기간      | 산출물                               |
| ----------- | ------- | --------------------------------- |
| 예약 모듈 구현    | Day 3–4 | schedules 테이블, RQ Worker          |
| 예약 UI & API | Day 4–5 | `/api/schedule`, `/api/schedules` |
| 통합 테스트      | Day 6   | 예약 실행‑취소 E2E                      |

---

## 11. 리스크 & 대응 (추가)

| 리스크          | 영향       | 대응                                 |
| ------------ | -------- | ---------------------------------- |
| Redis 장애     | 예약 발송 실패 | Fallback → SQLite polling, 모니터링 알림 |
| 잘못된 RRULE 입력 | 예약 실패    | 입력 검증 & 예시 제공                      |

---

## 12. 작업 우선순위 (요약)

1. DB 마이그레이션( `schedules` )
2. `/api/schedule` + RQ Worker
3. 예약 관리 UI(리스트/취소/즉시 실행)
4. E2E 테스트 → 배포

---

> **다음 작업:** RRULE UX 구체화(선택 UI vs. free‑text) 후 이슈 발행 🛠️
