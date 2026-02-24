# Windows EXE 업데이트 채널 운영 (반자동)

작성일: 2026-02-24

## 채널 목표

- 설치기 없이 `.exe` 교체 방식으로 업데이트합니다.
- 고객/지원팀은 배포본 교체 전 SHA256 검증을 수행합니다.

## 배포 산출물

- `newsletter_web.exe`
- `release-metadata.json`
- `SHA256SUMS.txt`
- `update-manifest.json`

## 매니페스트 생성

```bash
python scripts/devtools/generate_windows_update_manifest.py \
  --metadata dist/release-metadata.json \
  --output dist/update-manifest.json \
  --base-url "https://download.example.com/newsletter/windows"
```

## 운영 절차 (반자동)

1. 운영팀이 새 EXE와 3개 메타 파일을 배포 스토리지에 업로드
2. 지원팀이 `update-manifest.json`의 `download_url`로 파일 확보
3. `SHA256SUMS.txt`와 로컬 파일 해시 일치 확인
4. 기존 EXE 백업 후 신규 EXE 교체
5. `/health` 확인 후 업데이트 완료 처리

## 지원팀 점검표

- [ ] 다운로드 URL 접근 가능
- [ ] `version`과 공지 버전 일치
- [ ] SHA256 검증 통과
- [ ] `/health` 응답 정상
- [ ] 문제 발생 시 `support-bundle.zip` 수집
