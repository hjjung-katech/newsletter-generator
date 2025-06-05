# 로컬 개발 환경 설정 가이드

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
pip install -r requirements.txt
```

## 4. 환경 변수 설정

```bash
# .env.example을 복사하여 .env 파일 생성
cp .env.example .env

# .env 파일 편집하여 API 키 등 설정
# 필수: GEMINI_API_KEY, SERPER_API_KEY
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

## 6. 디렉토리 구조 확인

프로젝트는 다음과 같은 디렉토리들을 자동으로 생성합니다:

```
newsletter-generator/
├── output/                     # 생성된 뉴스레터 파일
│   ├── intermediate_processing/  # 중간 처리 파일
│   ├── email_tests/            # 이메일 테스트 결과
│   └── test_results/           # 테스트 결과
├── debug_files/                # 디버그 파일 (자동 생성)
└── web/
    └── storage.db              # 웹앱 데이터베이스 (자동 생성)
```

## 7. 개발 모드 실행

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

## 8. 데이터베이스 관리

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

## 9. 디버그 파일 정리

디버그 파일이 과도하게 쌓인 경우:

```bash
# 디버그 파일을 아카이브로 이동
python cleanup_debug_files.py --action move

# 디버그 파일 완전 삭제
python cleanup_debug_files.py --action delete
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