# Newsletter Generator
[English](README.md) | [한국어](README.ko.md)

[![Main CI](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/main-ci.yml/badge.svg?branch=main)](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/main-ci.yml)
[![Docs Quality](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/docs-quality.yml/badge.svg?branch=main)](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/docs-quality.yml)
[![Security Scan](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/security-scan.yml/badge.svg)](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/security-scan.yml)
[![Python 3.11 | 3.12](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Deploy Guide (Railway)](https://img.shields.io/badge/deploy-Railway-0B0D0E?logo=railway)](docs/setup/RAILWAY_DEPLOYMENT.md)

Operator-facing workflow system for Korean news curation and newsletter delivery.

Built for internal operators managing recurring newsletter generation, review, approval, and distribution workflows.

- Collect news by keyword or domain and generate structured HTML newsletters
- Preview, approve, and send through a web-based operator workflow
- Schedule recurring runs with retry safety and execution history
- Distribute via email with deduplication and outbox safety

## Quick Demo
Static preview of the default `compact` output shape.

**Input**

```text
Domain: Automotive
Keywords: autonomous driving, ADAS, Tesla FSD, Waymo
```

**Output**

```md
# Maintainer Communication Brief
_Maintainer workflow automation · Issue 14 · 2026-03-19_

_Turn weekly project activity into a concise update teams can actually use._

Prepared for contributors, internal stakeholders, and partner teams.

## 🔥 Must-Read This Week
### Release notes drafts now start from merged pull requests
The weekly changelog is pre-assembled from merged PR metadata, leaving maintainers with a short editorial pass instead of a full rewrite.
_Project activity · 2026-03-19_

## Project Delivery
Updates that reduce repetitive maintainer coordination work.

- **Weekly digest draft is prepared from project activity and issue labels** (`Release workflow · 2026-03-19`)

## 📖 Definitions
- **Idempotency key:** A stable request identifier used to prevent duplicate jobs or duplicate email sends.

## 💡 Things to Watch
> Operators managing recurring digests can reduce review time by refining keyword sets and source policies as coverage patterns stabilize.
```

## Overview
Maintainers and teams spend significant time summarizing updates and rewriting information for different audiences. Newsletter Generator is built to reduce that manual effort by turning source notes into a clean newsletter that can be shared across community, product, and internal communication workflows.

The production app renders HTML newsletters in `compact`, `detailed`, and `email_compatible` styles. This README keeps a static English preview of the default `compact` structure so first-time visitors can understand the real layout quickly; the shipped production templates in this repository are currently Korean-oriented. This repository also keeps the operational guidance that matters for real use: support policy, environment-variable contracts, local setup, deployment references, and verification gates.

## Use Cases
- Operators managing recurring keyword-based newsletter generation, review, and distribution
- Small teams sharing cross-functional progress without asking engineers to hand-write summaries
- Internal teams sharing domain-specific technical updates across product, platform, and operations groups
- Communication automation for recurring community digests, stakeholder briefs, and team newsletters

## Features
- Collect news from Serper, RSS, and Naver sources by keyword or domain
- Generate HTML newsletters via AI summarization (LangGraph + multi-LLM pipeline)
- Preview, approve, and send through a web-based operator workflow
- Schedule recurring runs with retry safety, deduplication, and execution history
- Manage presets, source policies, and archive references from the web surface

## Example Output
Example of a generated newsletter:

<details><summary>Full example output</summary>

```md
# Maintainer Communication Brief
_Maintainer workflow automation · Issue 14 · 2026-03-19_

_Turn weekly project activity into a concise update teams can actually use._

Prepared for contributors, internal stakeholders, and partner teams.

## 🔥 Must-Read This Week
### Release notes drafts now start from merged pull requests
The weekly changelog is pre-assembled from merged PR metadata, leaving maintainers with a short editorial pass instead of a full rewrite.
_Project activity · 2026-03-19_

### Docs quality checks now catch broken anchors before publish
Maintainers can fix link and reference regressions before updates go out to contributors or internal readers.
_Docs pipeline · 2026-03-18_

## Project Delivery
Updates that reduce repetitive maintainer coordination work.

- **Weekly digest draft is prepared from project activity and issue labels** (`Release workflow · 2026-03-19`)
- **Issue intake wording was simplified so non-engineers can report docs and deployment gaps faster** (`Support workflow · 2026-03-18`)

## Contributor Experience
Improvements that make updates easier to consume across community and internal audiences.

- **A single onboarding summary now answers the most repeated contributor setup questions** (`Contributor docs · 2026-03-17`)
- **Cross-team platform notes are grouped into one digest instead of separate status emails** (`Internal communications · 2026-03-17`)

## 📖 Definitions
- **Idempotency key:** A stable request identifier used to prevent duplicate jobs or duplicate email sends.
- **Docs gate:** An automated check that verifies documentation links, required references, and policy consistency.

## 💡 Things to Watch
> Operators managing recurring digests can reduce review time by refining keyword sets and source policies as coverage patterns stabilize.

_Generated as an English compact preview of the production newsletter template._
```

</details>

## Why This Matters
Maintainers already spend their time reviewing contributions, triaging issues, and keeping releases moving. Communication work is necessary, but it should not become another manual backlog. This project directly reduces maintainer workload in communication-heavy workflows such as updates, release notes, and stakeholder reporting.

## Getting Started
1. Quick start: [`docs/setup/QUICK_START_GUIDE.md`](docs/setup/QUICK_START_GUIDE.md)
2. Support policy: [`docs/reference/support-policy.md`](docs/reference/support-policy.md)
3. Environment-variable contract: [`docs/reference/environment-variables.md`](docs/reference/environment-variables.md)
4. Local development: [`docs/setup/LOCAL_SETUP.md`](docs/setup/LOCAL_SETUP.md)
5. Verification gates: `python -m scripts.devtools.dev_entrypoint check`, `python -m scripts.devtools.dev_entrypoint check --full`

Supported runtime guidance is defined in the support policy. In short, Python 3.11 and 3.12 are the active targets, Linux is the canonical production server, Windows is the native desktop bundle target, and macOS is supported mainly for source-based development and smoke checks.

To run locally:

```bash
git clone https://github.com/hjjung-katech/newsletter-generator.git
cd newsletter-generator
python -m scripts.devtools.dev_entrypoint bootstrap
cp .env.example .env
python -m scripts.devtools.dev_entrypoint check
python -m scripts.devtools.dev_entrypoint run newsletter run --keywords "open source, maintainer tooling"
```

## CLI Usage
Canonical source checkout entrypoints:

```bash
python -m scripts.devtools.dev_entrypoint run web
python web/init_database.py
python -m scripts.devtools.dev_entrypoint run newsletter run --keywords "open source, maintainer tooling"
python -m scripts.devtools.dev_entrypoint run newsletter run --keywords "open source, maintainer tooling" --template-style compact
```

If the package is installed, the CLI entrypoint is also available as:

```bash
newsletter run --keywords "open source, maintainer tooling"
```

## Current Priorities
- Maintain stable generate/preview/send/history/schedule flows in the web surface (G1)
- Keep schedule, approval, preset, and source policy workflows regression-free (G2)
- Maintain shared core contract across CLI, scheduler, and web via `newsletter_core.public` (G3)
- Hold legacy runtime surface in maintenance mode — no structural reopening without explicit trigger (G4)
- Keep operational contracts, support policy, and documentation aligned to the same production reality (G5)

## Project Docs
| Purpose | Reference |
|---|---|
| Docs hub | [`docs/README.md`](docs/README.md) |
| Document inventory | [`docs/DOCUMENT_INVENTORY.md`](docs/DOCUMENT_INVENTORY.md) |
| Installation and onboarding | [`docs/setup/INSTALLATION.md`](docs/setup/INSTALLATION.md), [`docs/setup/QUICK_START_GUIDE.md`](docs/setup/QUICK_START_GUIDE.md) |
| Local development | [`docs/setup/LOCAL_SETUP.md`](docs/setup/LOCAL_SETUP.md), [`docs/dev/DEVELOPMENT_GUIDE.md`](docs/dev/DEVELOPMENT_GUIDE.md) |
| Support, API, and env contracts | [`docs/reference/support-policy.md`](docs/reference/support-policy.md), [`docs/reference/web-api.md`](docs/reference/web-api.md), [`docs/reference/environment-variables.md`](docs/reference/environment-variables.md) |
| Deployment | [`docs/setup/RAILWAY_DEPLOYMENT.md`](docs/setup/RAILWAY_DEPLOYMENT.md) |
| Repo strategy and hygiene | [`docs/dev/LONG_TERM_REPO_STRATEGY.md`](docs/dev/LONG_TERM_REPO_STRATEGY.md), [`docs/dev/REPO_HYGIENE_POLICY.md`](docs/dev/REPO_HYGIENE_POLICY.md) |

## Contributing
- RR template: [`.github/ISSUE_TEMPLATE/review-request.yml`](.github/ISSUE_TEMPLATE/review-request.yml)
- PR template: [`.github/pull_request_template.md`](.github/pull_request_template.md)
- Commit template: [`.gitmessage.txt`](.gitmessage.txt)
- Repo rules: [`AGENTS.md`](AGENTS.md)

## License
`LICENSE`
