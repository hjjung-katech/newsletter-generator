# Support Policy

이 문서는 저장소의 지원 계약 SSOT입니다.

- 기준 브랜치/커밋: `main@5ca08544f1edb657b8e851e6cbe27f2d530c4907`
- 기준일: 2026-03-10
- 선택 전략: `Option B. Server parity + desktop exception`

## Decision Summary

- core runtime은 OS-neutral을 유지한다.
- Linux는 canonical production server다.
- Windows는 canonical native desktop bundle 대상이다.
- macOS는 2차 지원이며 source-based development와 smoke 중심이다.
- contributor-facing canonical entrypoint는 `python -m scripts.devtools.dev_entrypoint`다.
- Makefile과 shell script는 현재 contributor automation wrapper로 남아 있지만, 아키텍처 계약의 정본은 아니다.
- CI gate는 이 문서의 지원 계약을 비대칭적으로 집행한다. Linux는 full unit/package/container 검증, Windows는 source smoke + EXE release surface, macOS는 source smoke + runtime subset을 기준으로 유지한다.

## OS Support Contract

| OS | 지원 등급 | source 개발 | 현재 자동 검증 | production server | native bundle | 비고 |
|---|---|---|---|---|---|---|
| Linux | 1차 지원 | 정식 지원 | unit (py3.11/3.12) + release preflight + manifest inventory + packaging truth + source smoke + container smoke + mock/integration push gate | canonical | 비정본 | canonical packaging target은 Dockerfile 기반 Linux container image이며, 현재 repo-managed promoted release channel은 Railway/Nixpacks source deploy |
| Windows | 1차 지원 | 정식 지원 | source smoke + runtime subset + PyInstaller build + EXE smoke + release artifact validation | 비정본 | canonical | source 개발과 native desktop release surface를 같은 CI 파이프라인에서 검증한다 |
| macOS | 2차 지원 | source/smoke 중심 | source smoke + runtime subset | 비정본 | 미지원 | native packaging은 추가하지 않고 source-based development parity만 유지 |

## Python Version Policy

| Python | 상태 | 계약 |
|---|---|---|
| 3.11 | 정식 지원 | required CI/release target |
| 3.12 | 정식 지원 | required CI/release target |
| 3.10 | legacy transition only | 2026-06-30까지 migration-only. required CI 대상이 아니며 신규 지원 약속을 하지 않는다 |
| 3.13 | experimental source-only | contributor/local smoke 용도만 허용. release classifier와 required CI 대상이 아니다 |

## Canonical Runtimes and Artifacts

| 사용처 | 정본 | 현재 저장소 기준 truth |
|---|---|---|
| 개발(공통) | source checkout + Python entrypoint | `python -m scripts.devtools.dev_entrypoint <bootstrap|check|run ...>` |
| 로컬 source 웹 런타임 | Flask source runtime | contributor-facing run surface는 `python -m scripts.devtools.dev_entrypoint run web`이며, 실제 런타임 엔트리포인트는 `python -m web.app`다. 기본 포트는 `8000` (`web.app`, `.env.example`) |
| 로컬 source CLI 런타임 | newsletter CLI | contributor-facing run surface는 `python -m scripts.devtools.dev_entrypoint run newsletter -- ...`이며, 실제 런타임 엔트리포인트는 `python -m newsletter ...`다 |
| Linux server packaging | Dockerfile 기반 Linux container image | canonical packaging target. `docker build`가 패키징 truth이며, promoted Docker image release lane은 아직 운영하지 않는다 |
| Linux server 운영 | Railway/Nixpacks source deploy | 현재 repo-managed promoted release channel truth. canonical production server 계약은 Linux 기준이지만, promoted release channel과 packaging target은 구분한다 |
| Windows desktop 배포 | PyInstaller EXE | 정식 release surface는 `dist/newsletter_web.exe`, `release-metadata.json`, `SHA256SUMS.txt`, `support-bundle.zip`이다. `update-manifest.json`은 release-gated/update-channel 경로에서만 추가된다 |
| PyPI package | wheel/sdist | PyPI는 정식 end-user 릴리즈 채널이 아니다. `newsletter`/`newsletter_core` Python package subset 빌드 산출물일 뿐이며 canonical `web/` server runtime이나 Windows desktop release surface를 대체하지 않는다 |

## Approved Exceptions

- frozen/non-frozen 분기는 `web/runtime_paths.py`, `web/runtime_hook.py`, packaging entrypoint에만 둔다.
- Windows UTF-8/console shutdown 처리는 edge/runtime bootstrap 계층에서만 허용한다.
- Windows EXE packaging entrypoint는 현재 compatibility default port `5000`을 사용한다.
- source runtime의 canonical local port는 `8000`이며, Windows EXE 예외는 packaging 계층 문서에서 별도로 유지한다.

## Non-goals on This Commit

- macOS native desktop bundle
- Linux native desktop bundle
- Windows를 canonical production multi-service server로 승격
- promoted Docker image release lane
- PyPI end-user install을 정식 배포 채널로 승격

## Documentation Rules

- 지원 범위가 바뀌면 이 문서를 먼저 수정한다.
- `README.md`, 설치 문서, 개발 문서, CI 가이드는 이 문서를 링크하고 요약만 유지한다.
- 문서가 현재 CI/packaging/release truth보다 앞서가면 안 된다.
