#!/usr/bin/env python3
"""Verify GitHub controls required for Windows release delivery."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_REQUIRED_PATTERNS = ["main", "release", "release/*"]


def _gh_json(args: list[str]) -> Any:
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit((result.stdout + result.stderr).strip())
    return json.loads(result.stdout)


def _resolve_repo(repo: str) -> tuple[str, str]:
    if repo:
        if "/" not in repo:
            raise SystemExit(f"invalid --repo format: {repo} (expected owner/name)")
        owner, name = repo.split("/", maxsplit=1)
        return owner.strip(), name.strip()

    payload = _gh_json(["repo", "view", "--json", "nameWithOwner"])
    full_name = str(payload["nameWithOwner"])
    owner, name = full_name.split("/", maxsplit=1)
    return owner.strip(), name.strip()


def _branch_protection_rules(owner: str, repo: str) -> list[dict[str, Any]]:
    query = f"""
query {{
  repository(owner: "{owner}", name: "{repo}") {{
    branchProtectionRules(first: 100) {{
      nodes {{
        pattern
        isAdminEnforced
        requiresStatusChecks
        requiresStrictStatusChecks
        requiredStatusCheckContexts
      }}
    }}
  }}
}}
""".strip()
    payload = _gh_json(["api", "graphql", "-f", f"query={query}"])
    return payload["data"]["repository"]["branchProtectionRules"]["nodes"]


def _load_names(args: list[str]) -> set[str]:
    payload = _gh_json(args)
    return {str(item["name"]) for item in payload}


def _check_required_name(
    existing: set[str],
    required: str,
    label: str,
    errors: list[str],
) -> bool:
    if required in existing:
        return True
    errors.append(f"missing {label}: {required}")
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="")
    parser.add_argument("--required-check", default="Build Check (windows-latest)")
    parser.add_argument(
        "--required-pattern",
        action="append",
        default=[],
        help=(
            "Branch protection pattern to require. Repeatable. "
            "Default: main, release, release/*"
        ),
    )
    parser.add_argument("--required-variable", default="WINDOWS_UPDATE_BASE_URL")
    parser.add_argument("--required-secret", default="WINDOWS_OV_CERT_SHA1")
    parser.add_argument("--environment", default="production")
    parser.add_argument(
        "--require-admin-enforced",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--require-strict-status-checks",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--require-environment-variable",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--require-environment-secret",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    parser.add_argument(
        "--require-repo-variable",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--require-repo-secret",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    required_patterns = args.required_pattern or list(DEFAULT_REQUIRED_PATTERNS)
    owner, repo = _resolve_repo(args.repo)
    rules = _branch_protection_rules(owner, repo)
    rules_by_pattern = {str(rule["pattern"]): rule for rule in rules}

    repo_variable_names = _load_names(["variable", "list", "--json", "name"])
    repo_secret_names = _load_names(["secret", "list", "--json", "name"])
    env_variable_names = _load_names(
        ["variable", "list", "--env", args.environment, "--json", "name"]
    )
    env_secret_names = _load_names(
        ["secret", "list", "--env", args.environment, "--json", "name"]
    )

    errors: list[str] = []
    branch_results: dict[str, dict[str, Any]] = {}
    for pattern in required_patterns:
        rule = rules_by_pattern.get(pattern)
        if rule is None:
            errors.append(f"missing branch protection rule: {pattern}")
            branch_results[pattern] = {
                "exists": False,
                "admin_enforced": False,
                "requires_status_checks": False,
                "requires_strict_status_checks": False,
                "has_required_check": False,
                "required_status_checks": [],
            }
            continue

        checks = [str(value) for value in rule.get("requiredStatusCheckContexts", [])]
        has_required_check = args.required_check in checks
        if not bool(rule.get("requiresStatusChecks", False)):
            errors.append(f"{pattern}: requiresStatusChecks must be true")
        if args.require_admin_enforced and not bool(rule.get("isAdminEnforced", False)):
            errors.append(f"{pattern}: isAdminEnforced must be true")
        if args.require_strict_status_checks and not bool(
            rule.get("requiresStrictStatusChecks", False)
        ):
            errors.append(f"{pattern}: requiresStrictStatusChecks must be true")
        if not has_required_check:
            errors.append(f"{pattern}: required check missing: {args.required_check}")

        branch_results[pattern] = {
            "exists": True,
            "admin_enforced": bool(rule.get("isAdminEnforced", False)),
            "requires_status_checks": bool(rule.get("requiresStatusChecks", False)),
            "requires_strict_status_checks": bool(
                rule.get("requiresStrictStatusChecks", False)
            ),
            "has_required_check": has_required_check,
            "required_status_checks": checks,
        }

    repo_variable_ok: bool | None = None
    repo_secret_ok: bool | None = None
    env_variable_ok: bool | None = None
    env_secret_ok: bool | None = None

    if args.require_repo_variable:
        repo_variable_ok = _check_required_name(
            repo_variable_names,
            args.required_variable,
            "repo variable",
            errors,
        )
    if args.require_repo_secret:
        repo_secret_ok = _check_required_name(
            repo_secret_names,
            args.required_secret,
            "repo secret",
            errors,
        )
    if args.require_environment_variable:
        env_variable_ok = _check_required_name(
            env_variable_names,
            args.required_variable,
            f"environment({args.environment}) variable",
            errors,
        )
    if args.require_environment_secret:
        env_secret_ok = _check_required_name(
            env_secret_names,
            args.required_secret,
            f"environment({args.environment}) secret",
            errors,
        )

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo": f"{owner}/{repo}",
        "required": {
            "branch_patterns": required_patterns,
            "required_check": args.required_check,
            "required_variable": args.required_variable,
            "required_secret": args.required_secret,
            "environment": args.environment,
            "require_admin_enforced": args.require_admin_enforced,
            "require_strict_status_checks": args.require_strict_status_checks,
            "require_repo_variable": args.require_repo_variable,
            "require_repo_secret": args.require_repo_secret,
            "require_environment_variable": args.require_environment_variable,
            "require_environment_secret": args.require_environment_secret,
        },
        "branch_protection": branch_results,
        "controls": {
            "repo_variable_present": repo_variable_ok,
            "repo_secret_present": repo_secret_ok,
            "environment_variable_present": env_variable_ok,
            "environment_secret_present": env_secret_ok,
        },
        "present_names": {
            "repo_variables": sorted(repo_variable_names),
            "repo_secrets": sorted(repo_secret_names),
            "environment_variables": sorted(env_variable_names),
            "environment_secrets": sorted(env_secret_names),
        },
        "errors": errors,
        "passed": not errors,
    }

    print(json.dumps(summary, indent=2, ensure_ascii=True))
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(summary, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )

    if errors:
        raise SystemExit(
            f"github release controls check failed with {len(errors)} error(s)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
