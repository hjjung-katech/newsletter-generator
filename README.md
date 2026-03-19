# Newsletter Generator
[English](README.md) | [한국어](README.ko.md)

[![Main CI](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/main-ci.yml/badge.svg?branch=main)](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/main-ci.yml)
[![Docs Quality](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/docs-quality.yml/badge.svg?branch=main)](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/docs-quality.yml)
[![Security Scan](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/security-scan.yml/badge.svg?branch=main)](https://github.com/hjjung-katech/newsletter-generator/actions/workflows/security-scan.yml)
[![Python 3.11 | 3.12](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Deploy Guide (Railway)](https://img.shields.io/badge/deploy-Railway-0B0D0E?logo=railway)](docs/setup/RAILWAY_DEPLOYMENT.md)

Automates turning raw project updates into structured newsletters, reducing maintainer communication overhead.

Built for open-source maintainers, small teams, and internal technical communication workflows.

- Turn raw notes into shareable newsletter drafts
- Reduce time spent on release notes and recurring updates
- Usable by non-engineers through a web-based workflow
- Supports cross-platform use and email distribution

## Quick Demo
**Input**

```text
Title: Internal Update

[Software]
- Release notes draft is ready.
- Support inbox volume dropped this week.

[Mobility]
- Charging map refresh now runs hourly.
- Field-test telemetry parsing became more stable.
```

**Output**

```md
# Internal Update

## Software
- Release notes draft is ready.
- Support inbox volume dropped this week.

## Mobility
- Charging map refresh now runs hourly.
- Field-test telemetry parsing became more stable.
```

## Overview
Maintainers and teams spend significant time summarizing updates and rewriting information for different audiences. Newsletter Generator is built to reduce that manual effort by turning source notes into a clean newsletter that can be shared across community, product, and internal communication workflows.

This repository also keeps the operational guidance that matters for real use: support policy, environment-variable contracts, local setup, deployment references, and verification gates. The root README stays focused on the main story and entrypoints, while `docs/` remains the source of truth for detailed workflows.

## Use Cases
- Open-source maintainers sending weekly or monthly project updates to contributors and users
- Small teams sharing cross-functional progress without asking engineers to hand-write summaries
- Internal teams sharing domain-specific technical updates across product, platform, and operations groups
- Communication automation for recurring community digests, stakeholder briefs, and team newsletters

## Features
- Automatically summarize raw updates into structured, shareable newsletters
- Generate clean newsletter drafts that are ready for community or internal distribution
- Reduce time spent on release notes, status reporting, and recurring update summaries
- Support email distribution for recurring communication workflows
- Keep the workflow usable for non-engineers through a web-based, cross-platform experience

## Example Output
Example of a generated newsletter:

```md
# Maintainer Weekly Brief
Prepared for contributors, internal stakeholders, and partner teams.

## AI
- The model evaluation guide was rewritten into a single quick-start, which cut repeated onboarding questions from new contributors.
- Two flaky benchmark jobs were moved to nightly runs, reducing noise in the pull request queue and helping reviews land faster.
- A community proposal for structured prompt fixtures is ready for maintainer review after early feedback from three external contributors.

## Mobility
- The fleet telemetry parser now handles delayed device events more reliably, lowering the amount of manual triage after field tests.
- Charging map refreshes were moved to an hourly schedule so support teams and internal operators now see the same station status.
- A draft adapter guide for municipal traffic feeds is being reviewed internally before the integration work opens to outside contributors.

## Software
- Release highlights are now drafted automatically from merged pull requests, leaving maintainers with a short final review instead of a full rewrite.
- The issue intake template was simplified for non-engineering teammates, making docs gaps and deployment regressions easier to report.
- A small packaging fix removed an extra Windows setup step, which should reduce support churn for community adopters and internal teams.
```

## Why This Matters
Maintainers already spend their time reviewing contributions, triaging issues, and keeping releases moving. Communication work is necessary, but it should not become another manual backlog. This project directly reduces maintainer workload in communication-heavy workflows such as updates, release notes, and stakeholder reporting.

## Start Here
1. Quick start: [`docs/setup/QUICK_START_GUIDE.md`](docs/setup/QUICK_START_GUIDE.md)
2. Support policy: [`docs/reference/support-policy.md`](docs/reference/support-policy.md)
3. Environment-variable contract: [`docs/reference/environment-variables.md`](docs/reference/environment-variables.md)
4. Local development: [`docs/setup/LOCAL_SETUP.md`](docs/setup/LOCAL_SETUP.md)
5. Verification gates: `python -m scripts.devtools.dev_entrypoint check`, `python -m scripts.devtools.dev_entrypoint check --full`

Supported runtime guidance is defined in the support policy. In short, Python 3.11 and 3.12 are the active targets, Linux is the canonical production server, Windows is the native desktop bundle target, and macOS is supported mainly for source-based development and smoke checks.

## Getting Started
The fastest way to try the project is the bundled demo CLI. It uses plain text input and generates a Markdown newsletter in seconds.
You can generate your first newsletter in under a minute:

```bash
git clone https://github.com/hjjung-katech/newsletter-generator.git
cd newsletter-generator
python main.py --input sample_input.txt
```

If your machine exposes Python as `python3`, use `python3` in the commands above.

To save the generated newsletter to a file:

```bash
python main.py --input sample_input.txt --output newsletter.md
```

For the fuller repository workflow:

```bash
python -m scripts.devtools.dev_entrypoint bootstrap
cp .env.example .env
python -m scripts.devtools.dev_entrypoint check
```

## CLI Usage
Demo CLI:

```bash
python main.py --input sample_input.txt
python main.py --input sample_input.txt --output newsletter.md
python main.py --text $'Title: Internal Update\n[Software]\n- Release notes draft is ready.\n- Support inbox volume dropped this week.'
python main.py --sample
```

Canonical source checkout entrypoints:

```bash
python -m scripts.devtools.dev_entrypoint run web
python web/init_database.py
python -m scripts.devtools.dev_entrypoint run newsletter run --keywords "open source, maintainer tooling"
```

If the package is installed, the CLI entrypoint is also available as:

```bash
newsletter run --keywords "open source, maintainer tooling"
```

## Roadmap
- GitHub integration for pulling updates directly from repositories
- Pull request and issue summaries for recurring maintainer digests
- Release note generation for changelogs and stakeholder updates

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
