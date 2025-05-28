# 설치 가이드

Newsletter Generator의 설치 및 초기 설정에 대한 상세한 가이드입니다.

## 📋 목차

1. [시스템 요구사항](#시스템-요구사항)
2. [설치 방법](#설치-방법)
3. [환경 설정](#환경-설정)
4. [API 키 설정](#api-키-설정)
5. [설치 확인](#설치-확인)
6. [문제 해결](#문제-해결)

## 시스템 요구사항

### 필수 요구사항

- **Python**: 3.10 이상
- **운영체제**: Windows 10+, macOS 10.14+, Linux (Ubuntu 18.04+)
- **메모리**: 최소 4GB RAM (권장 8GB)
- **디스크 공간**: 최소 1GB 여유 공간

### 권장 요구사항

- **Python**: 3.11 (최신 안정 버전)
- **메모리**: 8GB RAM 이상
- **네트워크**: 안정적인 인터넷 연결 (API 호출용)

### Python 버전 확인

```bash
python --version
# 또는
python3 --version
```

Python이 설치되어 있지 않다면 [python.org](https://www.python.org/downloads/)에서 다운로드하세요.

## 설치 방법

### 방법 1: 개발 설치 (권장)

개발 및 커스터마이징을 위한 설치 방법입니다.

```bash
# 1. 저장소 클론
git clone https://github.com/username/newsletter-generator.git
cd newsletter-generator

# 2. 가상환경 생성
python -m venv .venv

# 3. 가상환경 활성화
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

# 4. 의존성 설치
pip install --upgrade pip
pip install -r requirements.txt

# 5. 개발 모드로 설치
pip install -e .
```

### 방법 2: PyPI 설치 (향후 지원 예정)

```bash
# 가상환경 생성 및 활성화
python -m venv newsletter-env
source newsletter-env/bin/activate  # macOS/Linux
# 또는
newsletter-env\Scripts\activate     # Windows

# PyPI에서 설치
pip install newsletter-generator
```

### 방법 3: Docker 설치 (향후 지원 예정)

```bash
# Docker 이미지 빌드
docker build -t newsletter-generator .

# 컨테이너 실행
docker run -it --env-file .env newsletter-generator
```

## 환경 설정

### 1. 환경 변수 파일 생성

```bash
# 예제 파일 복사
cp .env.example .env

# 환경 변수 파일 편집
nano .env  # Linux/macOS
notepad .env  # Windows
```

### 2. 기본 디렉토리 구조

설치 후 다음과 같은 디렉토리 구조가 생성됩니다:

```
newsletter-generator/
├── .env                    # 환경 변수 설정
├── .env.example           # 환경 변수 예제
├── newsletter/            # 메인 패키지
├── templates/             # HTML 템플릿
├── output/               # 생성된 파일들
├── docs/                 # 문서
├── tests/                # 테스트 파일
├── requirements.txt      # 의존성 목록
└── README.md            # 프로젝트 개요
```

### 3. 출력 디렉토리 생성

```bash
# 출력 디렉토리 생성 (자동으로 생성되지만 미리 만들 수 있음)
mkdir -p output/logs
mkdir -p output/intermediate_processing
```

## API 키 설정

Newsletter Generator는 여러 외부 서비스의 API를 사용합니다. 각 서비스별 API 키 설정 방법을 안내합니다.

### 필수 API 키

#### 1. Google Gemini Pro API

AI 요약 및 콘텐츠 생성에 사용됩니다.

1. [Google AI Studio](https://makersuite.google.com/app/apikey)에 접속
2. "Create API Key" 클릭
3. 생성된 API 키를 복사
4. `.env` 파일에 추가:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

#### 2. Serper.dev API

Google 검색 기반 뉴스 수집에 사용됩니다.

1. [Serper.dev](https://serper.dev/)에 가입
2. 대시보드에서 API 키 확인
3. `.env` 파일에 추가:

```bash
SERPER_API_KEY=your_serper_api_key_here
```

### 선택적 API 키

#### 3. 네이버 뉴스 API (선택사항)

한국어 뉴스 수집 품질 향상을 위해 사용됩니다.

1. [네이버 개발자 센터](https://developers.naver.com/main/)에 가입
2. "애플리케이션 등록" → "검색" API 선택
3. 클라이언트 ID와 시크릿 확인
4. `.env` 파일에 추가:

```bash
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret
```

#### 4. Postmark API (이메일 발송용)

뉴스레터 이메일 발송에 사용됩니다. (기존 SendGrid에서 Postmark로 변경됨)

1. [Postmark](https://postmarkapp.com/)에 가입
2. 서버(Server) 생성 후 **Server Token** 확인
3. **중요**: 발송자 이메일 주소를 Postmark에서 인증 (도메인 인증 필요)
4. `.env` 파일에 다음과 같이 추가:

```bash
POSTMARK_SERVER_TOKEN=your_postmark_server_token
EMAIL_SENDER=newsletter@yourdomain.com
```

**⚠️ 중요한 주의사항:**
- `EMAIL_SENDER`는 반드시 Postmark에서 인증된 도메인의 이메일이어야 합니다
- 발송자와 수신자가 같은 이메일 주소이면 안됩니다 (Hard Bounce 발생)
- 테스트 시에는 다른 이메일 주소를 수신자로 사용하세요

**Postmark 설정 확인:**
```bash
# 이메일 발송 기능 테스트 (실제 발송 없음)
newsletter test-email --to different-email@example.com --dry-run

# 실제 테스트 이메일 발송 (발송자와 다른 이메일로)
newsletter test-email --to different-email@example.com
```

**Hard Bounce 문제 해결:**
만약 이메일 주소가 비활성화(inactive)된 경우:
1. Postmark 대시보드 → Message Stream → Suppressions 탭
2. 해당 이메일 주소 검색
3. "Reactivate" 버튼 클릭하여 재활성화

#### 5. Google Drive API (파일 저장용)

Google Drive에 뉴스레터 저장에 사용됩니다.

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성
2. Google Drive API 활성화
3. 서비스 계정 생성 및 JSON 키 다운로드
4. 키 파일을 `credentials.json`으로 저장
5. `.env` 파일에 추가:

```bash
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

#### 6. LangSmith API (비용 추적용)

AI 사용 비용 추적에 사용됩니다.

1. [LangSmith](https://smith.langchain.com/)에 가입
2. 프로젝트 생성 및 API 키 확인
3. `.env` 파일에 추가:

```bash
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=your_project_name
```

### 추가 RSS 피드 설정

기본 RSS 피드 외에 추가 피드를 설정할 수 있습니다:

```bash
ADDITIONAL_RSS_FEEDS=https://example.com/rss1.xml,https://example.com/rss2.xml
```

## 설치 확인

### 1. 기본 설치 확인

```bash
# 버전 확인
newsletter --version

# 도움말 확인
newsletter --help
```

### 2. API 연결 테스트

```bash
# 간단한 키워드 추천 테스트
newsletter suggest --domain "AI" --count 5

# 기본 뉴스레터 생성 테스트
newsletter run --keywords "AI" --output-format html

# 이메일 발송 기능 테스트
newsletter test-email --to your-email@example.com --dry-run --max-per-source 2
```

### 3. 환경 변수 확인

```bash
# 필수 환경 변수 확인
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

required_keys = ['GEMINI_API_KEY', 'SERPER_API_KEY']
for key in required_keys:
    value = os.getenv(key)
    if value:
        print(f'{key}: ✓ (설정됨)')
    else:
        print(f'{key}: ✗ (누락)')
"
```

## 문제 해결

### 일반적인 설치 문제

#### 1. Python 버전 오류

```bash
# 오류: Python 3.10+ 필요
# 해결: Python 업그레이드
python --version
# Python 3.9.x인 경우 3.10+ 설치 필요
```

#### 2. 의존성 설치 실패

```bash
# 오류: pip install 실패
# 해결: pip 업그레이드 후 재시도
pip install --upgrade pip
pip install --upgrade setuptools wheel
pip install -r requirements.txt
```

#### 3. 가상환경 활성화 문제

```bash
# Windows PowerShell 실행 정책 오류
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 가상환경 재생성
deactivate
rm -rf .venv  # Linux/macOS
rmdir /s .venv  # Windows
python -m venv .venv
```

#### 4. 권한 문제

```bash
# Linux/macOS 권한 문제
sudo chown -R $USER:$USER newsletter-generator/
chmod +x newsletter-generator/

# Windows 관리자 권한으로 실행
# PowerShell을 관리자 권한으로 실행
```

### API 관련 문제

#### 1. API 키 인식 안됨

```bash
# .env 파일 위치 확인
ls -la .env

# 환경 변수 직접 설정 테스트
export GEMINI_API_KEY="your_key"  # Linux/macOS
set GEMINI_API_KEY=your_key       # Windows
```

#### 2. 네트워크 연결 문제

```bash
# 방화벽/프록시 확인
curl -I https://generativelanguage.googleapis.com
curl -I https://google.serper.dev

# 프록시 설정 (필요한 경우)
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
```

#### 3. API 할당량 초과

```bash
# API 사용량 확인
# Google AI Studio 대시보드에서 확인
# Serper.dev 대시보드에서 확인

# 임시 해결: 요청 수 제한
newsletter run --keywords "AI" --max-per-source 1 --period 1
```

### 성능 문제

#### 1. 메모리 부족

```bash
# 메모리 사용량 확인
python -c "
import psutil
print(f'Available memory: {psutil.virtual_memory().available / 1024**3:.1f} GB')
"

# 메모리 사용량 최적화
newsletter run --keywords "AI" --template-style compact --max-per-source 3
```

#### 2. 느린 실행 속도

```bash
# 병렬 처리 비활성화 (안정성 우선)
export NEWSLETTER_PARALLEL=false

# 캐시 디렉토리 정리
rm -rf output/cache/
```

### 로그 및 디버깅

#### 1. 상세 로그 활성화

```bash
# 디버그 모드로 실행
newsletter run --keywords "AI" --verbose

# 로그 파일 확인
tail -f output/logs/newsletter_$(date +%Y%m%d).log
```

#### 2. 중간 결과 저장

```bash
# 중간 처리 결과 저장
newsletter run --keywords "AI" --save-intermediate

# 중간 결과 파일 확인
ls -la output/intermediate_processing/
```

## 업그레이드

### 개발 설치 업그레이드

```bash
# 최신 코드 가져오기
git pull origin main

# 의존성 업데이트
pip install -r requirements.txt --upgrade

# 재설치
pip install -e . --force-reinstall
```

### PyPI 설치 업그레이드 (향후)

```bash
pip install --upgrade newsletter-generator
```

## 제거

### 완전 제거

```bash
# 가상환경 비활성화
deactivate

# 프로젝트 디렉토리 제거
rm -rf newsletter-generator/

# 가상환경 제거 (별도로 생성한 경우)
rm -rf newsletter-env/
```

## 다음 단계

설치가 완료되었다면:

1. [설정 가이드](CONFIGURATION.md)에서 상세한 설정 방법을 확인하세요
2. [사용자 가이드](../user/USER_GUIDE.md)에서 기본 사용법을 익히세요
3. [CLI 참조](../user/CLI_REFERENCE.md)에서 모든 명령어를 확인하세요
4. [예시 모음](../user/EXAMPLES.md)에서 다양한 사용 시나리오를 참고하세요 