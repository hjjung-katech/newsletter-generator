# Railway 배포 가이드

## 개요
Newsletter Generator를 Railway PaaS에 배포하기 위한 완전한 가이드입니다.

## 서비스 구성
Railway에서 다음과 같은 서비스들이 실행됩니다:

- **web**: Flask 웹 애플리케이션 (메인 API 서버)
- **worker**: Redis-RQ 백그라운드 워커 (뉴스레터 생성)
- **scheduler**: RRULE 기반 스케줄 실행기 (정기 발송)
- **redis**: Redis 인스턴스 (작업 큐 및 캐시)

## 필수 환경변수 설정

### 1. OpenAI API
```bash
OPENAI_API_KEY=sk-...
```

### 2. SendGrid 이메일 설정
```bash
SENDGRID_API_KEY=SG.xxx
FROM_EMAIL=newsletter@yourdomain.com
```

### 3. Google 뉴스 API (선택사항)
```bash
GOOGLE_NEWS_API_KEY=xxx  # News API 키
```

### 4. Flask 설정
```bash
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
```

### 5. Redis 연결 (자동 설정됨)
```bash
REDIS_URL=redis://redis:6379/0
```

## 배포 단계

### 1. Repository 연결
1. Railway 대시보드에서 "New Project" 클릭
2. GitHub repository 선택: `newsletter-generator`
3. Auto-deploy 활성화

### 2. 서비스 생성
Railway는 `railway.yml` 파일을 기반으로 자동으로 4개 서비스를 생성합니다:

```yaml
services:
  web:      # 메인 웹 애플리케이션
  worker:   # 백그라운드 작업 처리
  scheduler: # 스케줄 실행
  redis:    # Redis 인스턴스
```

### 3. 환경변수 설정
각 서비스에서 필요한 환경변수를 설정합니다:

**web 서비스:**
- `OPENAI_API_KEY`
- `SENDGRID_API_KEY`
- `FROM_EMAIL`
- `SECRET_KEY`
- `FLASK_ENV=production`

**worker 서비스:**
- `OPENAI_API_KEY`
- `SENDGRID_API_KEY`
- `FROM_EMAIL`
- `RQ_QUEUE=default`

**scheduler 서비스:**
- `OPENAI_API_KEY`
- `SENDGRID_API_KEY`
- `FROM_EMAIL`

### 4. 도메인 설정
1. Railway에서 제공하는 임시 도메인 확인
2. 커스텀 도메인 연결 (선택사항)

## 파일 구조
```
project/
├── web/
│   ├── app.py              # Flask 메인 애플리케이션
│   ├── worker.py           # RQ 워커
│   ├── schedule_runner.py  # 스케줄 실행기
│   ├── tasks.py            # 백그라운드 작업 정의
│   ├── mail.py             # 이메일 발송 모듈
│   ├── init_database.py    # DB 초기화
│   ├── storage.db          # SQLite 데이터베이스
│   └── requirements.txt    # Python 의존성
├── nixpacks.toml           # Nixpacks 빌드 설정
├── railway.yml             # Railway 서비스 정의
└── README.md
```

## 데이터베이스 초기화
배포 시 자동으로 SQLite 데이터베이스가 초기화됩니다:

```bash
python web/init_database.py --force
```

이 명령은 다음 테이블들을 생성합니다:
- `history`: 뉴스레터 생성 히스토리
- `schedules`: 정기 발송 예약 정보

## 모니터링 및 로그
- **헬스체크**: `/health` 엔드포인트
- **로그 확인**: Railway 대시보드에서 각 서비스 로그 모니터링
- **Redis 상태**: 웹 서비스의 `/health` 응답에서 확인

## 트러블슈팅

### 1. Redis 연결 오류
```bash
# Redis 서비스가 시작되었는지 확인
REDIS_URL=redis://redis:6379/0
```

### 2. 데이터베이스 초기화 실패
```bash
# 수동으로 데이터베이스 초기화
cd web && python init_database.py --force
```

### 3. 워커 실행 오류
```bash
# RQ 워커 로그 확인
python worker.py
```

### 4. 스케줄러 실행 확인
```bash
# 5분마다 스케줄 체크
python schedule_runner.py --interval 300
```

## API 엔드포인트

### 뉴스레터 생성
```bash
POST /api/generate
{
  "keywords": ["AI", "tech"],
  "email": "user@example.com"
}
```

### 스케줄 생성
```bash
POST /api/schedule
{
  "keywords": ["AI", "tech"],
  "email": "user@example.com",
  "rrule": "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9"
}
```

### 스케줄 조회
```bash
GET /api/schedules
```

### 스케줄 삭제
```bash
DELETE /api/schedule/{schedule_id}
```

### 즉시 실행
```bash
POST /api/schedule/{schedule_id}/run
```

## RRULE 예시

### 매주 월요일 오전 9시
```
FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0
```

### 매일 오전 8시
```
FREQ=DAILY;BYHOUR=8;BYMINUTE=0
```

### 매월 1일 오전 10시
```
FREQ=MONTHLY;BYMONTHDAY=1;BYHOUR=10;BYMINUTE=0
```

## 성능 최적화
- **웹 서비스**: 2개 워커로 설정
- **작업 타임아웃**: 10분 (긴 뉴스레터 생성 시간 고려)
- **스케줄 체크**: 5분 간격
- **Redis TTL**: 작업 결과 24시간 보관

## 보안 고려사항
- 모든 API 키는 환경변수로 관리
- HTTPS 자동 적용 (Railway 기본 제공)
- 데이터베이스는 서비스 내부에만 접근 가능 