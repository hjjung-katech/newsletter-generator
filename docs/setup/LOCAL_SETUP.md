# 로컬 개발 환경 설정 가이드

> 빠른 실행이 목적이라면 먼저 `QUICK_START_GUIDE.md`를 사용하세요.
> 이 문서는 로컬 개발/디버깅/운영 시뮬레이션(Redis, worker, scheduler) 상세 절차를 다룹니다.

## 1. 프로젝트 클론 및 기본 설정

```bash
git clone https://github.com/hjjung-katech/newsletter-generator.git
cd newsletter-generator
```

## 2. 가상환경 설정

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

## 3. 의존성 설치

```bash
# 기본 패키지 설치
pip install -r requirements.txt

# 웹 애플리케이션 의존성 추가 설치
pip install -r web/requirements.txt
```

## 4. 환경 변수 설정

> 환경변수 정본은 `../reference/environment-variables.md`를 기준으로 유지합니다.

### 자동 설정 (권장)
```bash
# 자동 환경 설정 스크립트 실행
python scripts/devtools/setup_env.py
```

### 수동 설정
```bash
# .env 파일 생성 (루트 디렉토리에)
# 필수 API 키들:

# AI 모델 (둘 중 하나 이상 필수)
GEMINI_API_KEY=your-gemini-api-key-here
OPENAI_API_KEY=your-openai-api-key-here

# 뉴스 검색 (필수)
SERPER_API_KEY=your-serper-api-key-here

# 이메일 발송 (선택사항)
POSTMARK_SERVER_TOKEN=your-postmark-server-token-here
EMAIL_SENDER=newsletter@yourdomain.com

# Flask 설정 (선택사항)
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
```

## 5. 웹 애플리케이션 데이터베이스 초기화

웹 인터페이스를 사용하려면 SQLite 데이터베이스를 초기화해야 합니다:

```bash
# web 디렉토리로 이동
cd web

# 데이터베이스 초기화
python init_database.py

# 또는 강제 재생성 (기존 DB 백업 후 새로 생성)
python init_database.py --force

# 데이터베이스 상태 확인
python init_database.py --verify-only
```

초기화 완료 후 다음 테이블들이 생성됩니다:
- `history`: 뉴스레터 생성 히스토리
- `schedules`: 정기 발송 예약 정보

## 6. 웹 애플리케이션 실행

### 기본 실행 (가장 간단한 방법)

```bash
# 웹 애플리케이션만 실행 (권장)
cd web
python app.py
```

웹 서버가 시작되면:
- **브라우저에서 http://localhost:5000 접속**
- Windows에서는 자동으로 Redis 없이 동작 (in-memory 처리)
- 백그라운드 작업은 별도 스레드로 처리

### 고급 설정 (프로덕션 환경 시뮬레이션)

Redis와 백그라운드 워커를 함께 실행하려면:

#### 1단계: Redis 서버 설치 및 실행

**Windows:**
```powershell
# 방법 1: Chocolatey를 사용한 설치 (권장)
choco install redis-64

# 방법 2: Scoop을 사용한 설치
scoop install redis

# 방법 3: 직접 다운로드
# https://github.com/microsoftarchive/redis/releases
# 또는 https://github.com/tporadowski/redis/releases (더 최신 버전)

# Redis 서버 실행
redis-server

# 또는 Windows 서비스로 실행 (설치에 따라 다름)
net start redis
```

> **💡 Windows 팁**:
> - Chocolatey가 없다면 [chocolatey.org](https://chocolatey.org/install)에서 설치
> - Scoop이 없다면 PowerShell에서 `iwr -useb get.scoop.sh | iex` 실행
> - 직접 다운로드 시 압축 해제 후 PATH에 추가 필요

**macOS:**
```bash
# Homebrew 사용
brew install redis
brew services start redis

# 또는 직접 실행
redis-server
```

**Linux (Ubuntu/Debian):**
```bash
# 설치
sudo apt update
sudo apt install redis-server

# 서비스 시작
sudo systemctl start redis
sudo systemctl enable redis  # 부팅 시 자동 시작

# 또는 직접 실행
redis-server
```

#### 2단계: 백그라운드 워커 실행 (별도 터미널)
```bash
cd web
python worker.py
```

#### 3단계: 스케줄러 실행 (별도 터미널, 선택사항)
```bash
cd web
python schedule_runner.py
```

#### 4단계: 웹 애플리케이션 실행
```bash
cd web
python app.py
```

## 7. 실행 모드별 특징

### 단독 실행 모드 (기본, 권장)
- **명령어**: `python web/app.py`
- **특징**:
  - Redis 불필요
  - 즉시 실행 가능
  - 백그라운드 작업은 스레드로 처리
  - Windows에서 자동으로 적용됨

### Redis + 워커 모드 (고급)
- **명령어**: Redis + `python web/worker.py` + `python web/app.py`
- **특징**:
  - Redis 서버 필요
  - 백그라운드 작업을 별도 프로세스로 처리
  - 스케줄링 기능 사용 가능
  - 프로덕션 환경과 동일

## 8. 웹 인터페이스 사용법

### 기본 기능
1. **뉴스레터 생성**: 키워드 입력 후 Generate 버튼 클릭
2. **결과 확인**: 생성 완료 후 View 버튼으로 뉴스레터 확인
3. **히스토리**: 이전에 생성한 뉴스레터 목록 확인

### API 엔드포인트
- **뉴스레터 생성**: `POST /api/generate`
- **작업 상태 확인**: `GET /api/status/{job_id}`
- **히스토리 조회**: `GET /api/history`
- **헬스체크**: `GET /health`

## 9. 디렉토리 구조 확인

프로젝트는 다음과 같은 디렉토리들을 자동으로 생성합니다:

```
newsletter-generator/
├── output/                     # 생성된 뉴스레터 파일
│   ├── intermediate_processing/  # 중간 처리 파일
│   ├── email_tests/            # 이메일 테스트 결과
│   └── test_results/           # 테스트 결과
├── debug_files/                # 디버그 파일 (자동 생성)
└── web/
    ├── storage.db              # 웹앱 데이터베이스 (자동 생성)
    ├── app.py                  # 메인 웹 애플리케이션
    ├── worker.py               # 백그라운드 워커 (선택사항)
    ├── schedule_runner.py      # 스케줄러 (선택사항)
    └── templates/              # HTML 템플릿
```

## 10. 개발 모드 실행

### CLI 모드
```bash
# 뉴스레터 생성
python -m newsletter.cli generate --keywords "AI,반도체" --email "your@email.com"
```

### 웹 애플리케이션 모드
```bash
cd web
python app.py
# 브라우저에서 http://localhost:5000 접속
```

## 11. 데이터베이스 관리

### 데이터베이스 백업
```bash
cd web
cp storage.db storage.db.backup_$(date +%Y%m%d_%H%M%S)
```

### 데이터베이스 재설정
```bash
cd web
python init_database.py --force
```

### 히스토리 정리 (선택사항)
```bash
# SQLite 명령어로 직접 정리
sqlite3 storage.db "DELETE FROM history WHERE created_at < datetime('now', '-30 days');"
```

## 12. 디버그 파일 정리

디버그 파일이 과도하게 쌓인 경우:

```bash
# 디버그 파일을 아카이브로 이동
python scripts/devtools/cleanup_debug_files.py --action move

# 디버그 파일 완전 삭제
python scripts/devtools/cleanup_debug_files.py --action delete
```

## 문제 해결

### 데이터베이스 관련 오류
```bash
# 데이터베이스 재생성
cd web
rm -f storage.db
python init_database.py
```

### 권한 관련 오류 (Windows)
```bash
# PowerShell을 관리자 권한으로 실행
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 패키지 설치 오류
```bash
# pip 업그레이드
python -m pip install --upgrade pip

# 캐시 정리 후 재설치
pip cache purge
pip install -r requirements.txt
```

### Redis 연결 오류 (고급 모드 사용 시)
```bash
# Redis 서버 상태 확인
redis-cli ping
# 응답: PONG
```

**Redis 서버 재시작:**

**Windows:**
```powershell
# 서비스로 실행 중인 경우
net stop redis
net start redis

# 또는 작업 관리자에서 redis-server 프로세스 종료 후 재시작
redis-server
```

**macOS:**
```bash
# Homebrew 서비스 재시작
brew services restart redis

# 또는 직접 실행 중인 경우 Ctrl+C로 중지 후 재시작
redis-server
```

**Linux:**
```bash
# systemd 서비스 재시작
sudo systemctl restart redis

# 또는 직접 실행 중인 경우 Ctrl+C로 중지 후 재시작
redis-server
```

### 웹 서버 포트 충돌
```bash
# 다른 포트로 실행
cd web
PORT=8000 python app.py
# 또는
python app.py --port 8000
```

## 추가 팁

### 개발 중 자동 재로드
```bash
# Flask 개발 서버의 자동 재로드 기능 사용
cd web
FLASK_ENV=development python app.py
```

### 로그 레벨 조정
```bash
# 상세한 로그 확인
cd web
LOG_LEVEL=DEBUG python app.py
```

### API 테스트
```bash
# 간단한 API 테스트
curl -X POST http://localhost:5000/api/generate \
  -H "Idempotency-Key: local-smoke-001" \
  -H "Content-Type: application/json" \
  -d '{"keywords": ["AI", "기술"], "period": 7}'
```

중복 요청을 같은 `Idempotency-Key`로 다시 보내면 `202`와 함께 `deduplicated=true`가 반환됩니다.

운영 안전성 스모크(멱등성/아웃박스)는 자동 스크립트로 점검할 수 있습니다.
```bash
BASE_URL=http://localhost:5000 make ops-safety-smoke
```
