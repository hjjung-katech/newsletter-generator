# Repo Hygiene Status Snapshot (2026-02-24)

이 문서는 리포 구조 개선 작업의 중간 마감 기록과 재시작 가이드입니다.

## 목적

- 현재까지 완료된 범위를 한 번에 확인할 수 있게 고정합니다.
- 다음 착수 시 같은 운영 프로세스(RR -> Branch -> Commit -> PR -> CI -> Merge)로 재개할 수 있게 합니다.
- "무엇을 먼저 할지"를 우선순위로 잠금합니다.

## 기준 시점

- 작성일: 2026-02-24
- 기준 브랜치: `main`
- 기준 상태: 로컬 작업트리 clean

## 이번 사이클 완료 범위

아래 PR이 머지되어 Week 1~2 기반 구조 정리와 워크플로 거버넌스가 반영되었습니다.

1. [PR #123](https://github.com/hjjung-katech/newsletter-generator/pull/123): RR 자동 종료 워크플로 추가
2. [PR #121](https://github.com/hjjung-katech/newsletter-generator/pull/121): `.githooks/pre-push`를 `scripts/devtools/hooks/pre-push`로 이관
3. [PR #119](https://github.com/hjjung-katech/newsletter-generator/pull/119): `.vscode` local-only 전환
4. [PR #117](https://github.com/hjjung-katech/newsletter-generator/pull/117): `output/`, `debug_files` local-only 전환
5. [PR #115](https://github.com/hjjung-katech/newsletter-generator/pull/115): `newsletter_core` 경로 평탄화

## 현재 지표

- 루트 tracked 엔트리 수: `32`
- repo-audit top-level 엔트리 수: `44`
- repo-audit 정책 warnings: `0`
- 기본 게이트 상태: `make check`, `make check-full` 통과 기준 유지

## 현재 루트 tracked 엔트리

```text
.agents
.dockerignore
.env.example
.github
.gitignore
.gitmessage.txt
.pre-commit-config.yaml
.release
.secrets.baseline
AGENTS.md
CHANGELOG.md
CODEOWNERS
Dockerfile
LICENSE
Makefile
README.md
apps
config
docs
newsletter
newsletter_core
nixpacks.toml
pyproject.toml
railway.yml
requirements-dev.txt
requirements-minimal.txt
requirements.txt
run_ci_checks.py
scripts
templates
tests
web
```

## 다음 작업 우선순위 (재시작 기준)

1. `apps/`, `config/`, `templates/`의 "과도기 유지" 종료 조건 확정
2. 루트 엔트리 `32 -> 30 이하`를 위한 최종 감축 후보 확정
3. 오래 열린 RR(issue #118, #116, #114, #112, #110, #108, #106) 정리 원칙 수립
4. repo hygiene 정책 문서(`REPO_HYGIENE_POLICY.md`)에 최종 타겟 상태 반영

## 재시작 체크리스트

다음 사이클 시작 시 아래를 먼저 확인합니다.

1. `git checkout main && git pull --ff-only`
2. `git status --short --branch`에서 clean 확인
3. RR 작성(`review-request` 라벨 + Delivery Unit ID 포함)
4. `codex/<scope>-<topic>` 브랜치 생성
5. PR 단위(2~6 커밋)로 작업 후 `make check`, `make check-full` 실행

## 다음에 이렇게 요청하면 바로 재개 가능

아래 문장 중 하나를 그대로 요청하면 동일한 방식으로 재시작할 수 있습니다.

```text
docs/dev/REPO_HYGIENE_STATUS_2026-02-24.md 기준으로 다음 우선순위 1번부터 RR->PR->CI->merge까지 끝까지 진행해줘.
```

```text
repo hygiene 다음 사이클 시작: main clean 확인 -> RR 생성 -> codex 브랜치 -> 작업/검증/PR/merge 순서로 자동 진행해줘.
```

```text
루트 엔트리를 30 이하로 줄이는 다음 배치를 이 스냅샷 문서 기준으로 실행해줘. 커밋/PR 분리해서 끝까지 진행해줘.
```

## 참고 정본 문서

- 전략 정본: `docs/dev/LONG_TERM_REPO_STRATEGY.md`
- 정책 정본: `docs/dev/REPO_HYGIENE_POLICY.md`
- 운영 표준: `docs/dev/WORKFLOW_TEMPLATES.md`
- 실행 요청 표준: `docs/dev/AGENT_SKILL_REQUEST_PLAYBOOK.md`
