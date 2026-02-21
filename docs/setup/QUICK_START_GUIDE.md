# Newsletter Generator 빠른 시작 가이드

## 🎯 목표
이 가이드를 따라하면 **5분 안에** Newsletter Generator 웹 인터페이스를 로컬에서 실행할 수 있습니다.

## 📋 사전 요구사항
- Python 3.8 이상
- Git
- 인터넷 연결

## 🚀 빠른 시작 (5분 완성)

### 1단계: 프로젝트 다운로드
```bash
git clone https://github.com/hjjung-katech/newsletter-generator.git
cd newsletter-generator
```

### 2단계: 가상환경 설정
```bash
# 가상환경 생성
python -m venv .venv

# 가상환경 활성화
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### 3단계: 패키지 설치
```bash
# 기본 패키지 설치
pip install -r requirements.txt

# 웹 애플리케이션 패키지 설치
pip install -r web/requirements.txt
```

### 4단계: 환경 설정 (자동)
```bash
# 자동 환경 설정 실행
python setup_env.py
```

설정 과정에서:
1. **API 키 입력**: Gemini API와 Serper API 키를 입력하세요
2. **이메일 설정**: Postmark 키는 선택사항입니다 (건너뛰기 가능)

### 5단계: 데이터베이스 초기화
```bash
cd web
python init_database.py
```

### 6단계: 웹 서버 실행
```bash
python app.py
```

### 7단계: 브라우저에서 접속
브라우저를 열고 **http://localhost:5000**에 접속하세요!

## 🎉 완료!
이제 Newsletter Generator를 사용할 수 있습니다.

---

## 📖 상세 가이드

### API 키 발급 방법

#### 1. Gemini API 키 (필수)
1. [Google AI Studio](https://aistudio.google.com/) 접속
2. "Get API key" 클릭
3. 새 프로젝트 생성 또는 기존 프로젝트 선택
4. API 키 복사

#### 2. Serper API 키 (필수)
1. [Serper](https://serper.dev/) 접속
2. 회원가입 또는 로그인
3. Dashboard에서 API 키 확인
4. 무료 플랜으로 2,500회 검색 가능

#### 3. Postmark API 키 (선택사항)
1. [Postmark](https://postmarkapp.com/) 접속
2. 회원가입 후 API 키 생성
3. 이메일 발송 기능을 위해 필요

### 수동 환경 설정

자동 설정이 실패한 경우, 루트 디렉토리에 `.env` 파일을 직접 생성하세요:

```bash
# .env 파일 내용
GEMINI_API_KEY=your-gemini-api-key-here
SERPER_API_KEY=your-serper-api-key-here
POSTMARK_SERVER_TOKEN=your-postmark-server-token-here  # 선택사항
EMAIL_SENDER=newsletter@yourdomain.com  # 선택사항
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
```

## 🖥️ 웹 인터페이스 사용법

### 뉴스레터 생성
1. 키워드 입력 (예: "AI, 반도체, 기술")
2. 기간 선택 (1일, 7일, 14일, 30일)
3. "Generate Newsletter" 버튼 클릭
4. 생성 완료 후 "View" 버튼으로 결과 확인

### 기능 설명
- **History**: 이전에 생성한 뉴스레터 목록
- **Status**: 현재 진행 중인 작업 상태
- **Email**: 생성된 뉴스레터를 이메일로 발송 (Postmark 설정 필요)

## 🔧 문제 해결

### 자주 발생하는 문제

#### 1. "ModuleNotFoundError" 오류
```bash
# 해결방법: 패키지 재설치
pip install -r requirements.txt
pip install -r web/requirements.txt
```

#### 2. "Permission denied" 오류 (Windows)
```bash
# 해결방법: PowerShell을 관리자 권한으로 실행
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### 3. 포트 5000이 사용 중인 경우
```bash
# 해결방법: 다른 포트 사용
PORT=8000 python app.py
# 브라우저에서 http://localhost:8000 접속
```

#### 4. API 키 관련 오류
- `.env` 파일이 루트 디렉토리에 있는지 확인
- API 키가 올바른지 확인
- Gemini API와 Serper API 키는 필수

#### 5. 데이터베이스 오류
```bash
# 해결방법: 데이터베이스 재생성
cd web
rm -f storage.db  # Windows: del storage.db
python init_database.py
```

### 로그 확인
```bash
# 상세한 로그로 문제 진단
cd web
LOG_LEVEL=DEBUG python app.py
```

## 🔄 업데이트 방법

```bash
# 최신 버전으로 업데이트
git pull origin main

# 패키지 업데이트
pip install -r requirements.txt --upgrade
pip install -r web/requirements.txt --upgrade

# 데이터베이스 업데이트 (필요시)
cd web
python init_database.py --force
```

## 📁 프로젝트 구조

```
newsletter-generator/
├── .env                    # 환경변수 (직접 생성)
├── web/
│   ├── app.py             # 메인 웹 애플리케이션
│   ├── storage.db         # 데이터베이스 (자동 생성)
│   └── templates/         # HTML 템플릿
├── output/                # 생성된 뉴스레터 (자동 생성)
└── debug_files/           # 디버그 파일 (자동 생성)
```

## 🚀 다음 단계

### CLI 사용법
웹 인터페이스 외에도 명령줄에서 직접 사용할 수 있습니다:

```bash
# CLI로 뉴스레터 생성
python -m newsletter.cli generate --keywords "AI,반도체" --email "your@email.com"
```

### 고급 기능
- **스케줄링**: 정기적인 뉴스레터 발송
- **이메일 발송**: Postmark를 통한 자동 이메일 발송
- **템플릿 커스터마이징**: HTML 템플릿 수정

### 프로덕션 배포
Railway, Heroku 등의 클라우드 플랫폼에 배포할 수 있습니다.
자세한 내용은 `docs/setup/RAILWAY_DEPLOYMENT.md`를 참조하세요.

## 🆘 도움이 필요한 경우

1. **문서 확인**:
   - `docs/setup/LOCAL_SETUP.md` (상세한 로컬 설정)
   - `docs/setup/RAILWAY_DEPLOYMENT.md` (프로덕션 배포)

2. **이슈 리포트**:
   GitHub Issues에 문제를 보고해주세요.

3. **로그 수집**:
   문제 발생 시 터미널의 전체 로그를 복사해서 제공해주세요.

---

**🎉 Newsletter Generator를 사용해주셔서 감사합니다!**
