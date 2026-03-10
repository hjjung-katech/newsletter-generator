"""Canonical developer entrypoint for local bootstrap, gates, and run flows.

This module keeps contributor-facing workflow logic in Python so that
Makefile/shell wrappers can stay thin and clone-path agnostic.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIRS = ["newsletter", "tests", "web", "scripts", "apps", "newsletter_core"]
RUNTIME_CHANGE_PATTERN = re.compile(r"^(newsletter|web)/.*\.py$")
FORBIDDEN_DOC_TOKENS = (
    "SENDGRID_API_KEY",
    "POSTMARK_TOKEN",
    "POSTMARK_API_TOKEN",
)
DOC_CONSISTENCY_PATHS = (
    Path("README.md"),
    Path("docs/setup"),
    Path(".env.example"),
    Path("apps/experimental/.env.example"),
    Path("web/requirements.txt"),
)
MOCK_ENV = {
    "MOCK_MODE": "true",
    "TESTING": "1",
    "OPENAI_API_KEY": "test-key",
    "SERPER_API_KEY": "test-key",
    "GEMINI_API_KEY": "test-key",
    "ANTHROPIC_API_KEY": "test-key",
    "POSTMARK_SERVER_TOKEN": "dummy-token",
    "EMAIL_SENDER": "test@example.com",
}
NEWSLETTER_SMOKE = (
    "from unittest.mock import patch; "
    "from newsletter_core.public.generation import GenerateNewsletterRequest, "
    "generate_newsletter; "
    "sample='<html><head><title>Smoke</title></head><body>ok</body></html>'; "
    "info={'step_times': {'collect': 0.1}, 'total_time': 0.2}; "
    "p1=patch('newsletter_core.public.generation.graph.generate_newsletter', "
    "return_value=(sample, 'success')); "
    "p2=patch('newsletter_core.public.generation.graph.get_last_generation_info', "
    "return_value=info); "
    "p1.start(); p2.start(); "
    "r=generate_newsletter(GenerateNewsletterRequest(keywords='AI', period=7)); "
    "p2.stop(); p1.stop(); "
    "assert r['status']=='success'; "
    "assert r['title']=='Smoke'; "
    "assert '<html' in r['html_content'].lower(); "
    "print('newsletter-smoke: ok')"
)


@dataclass(frozen=True)
class RepoPaths:
    repo_root: Path
    local_dir: Path
    artifacts_dir: Path
    coverage_dir: Path
    debug_dir: Path
    default_venv_dir: Path
    legacy_venv_dir: Path


def repo_paths(repo_root: Path = REPO_ROOT) -> RepoPaths:
    local_dir = repo_root / ".local"
    return RepoPaths(
        repo_root=repo_root,
        local_dir=local_dir,
        artifacts_dir=local_dir / "artifacts",
        coverage_dir=local_dir / "coverage",
        debug_dir=local_dir / "debug_files",
        default_venv_dir=local_dir / "venv",
        legacy_venv_dir=repo_root / ".venv",
    )


def venv_python(venv_dir: Path) -> Path:
    scripts_python = venv_dir / "Scripts" / "python.exe"
    if scripts_python.exists():
        return scripts_python
    return venv_dir / "bin" / "python"


def resolve_existing_venv_python(paths: RepoPaths) -> Path | None:
    for candidate in (paths.default_venv_dir, paths.legacy_venv_dir):
        python_path = venv_python(candidate)
        if python_path.exists():
            return python_path
    return None


def resolve_venv_dir(paths: RepoPaths) -> Path:
    python_path = resolve_existing_venv_python(paths)
    if python_path is None:
        return paths.default_venv_dir
    return python_path.parent.parent


def resolve_python(paths: RepoPaths, prefer_venv: bool = True) -> Path:
    if prefer_venv:
        python_path = resolve_existing_venv_python(paths)
        if python_path is not None:
            return python_path
    return Path(sys.executable)


def ensure_git_root(paths: RepoPaths) -> None:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=paths.repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit("git checkout required for developer entrypoint")
    git_root = Path(result.stdout.strip()).resolve()
    if git_root != paths.repo_root.resolve():
        raise SystemExit(
            f"git root mismatch: expected {paths.repo_root}, got {git_root}"
        )


def merged_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("NEWSLETTER_DEBUG_DIR", str(repo_paths().debug_dir))
    if extra:
        env.update(extra)
    return env


def print_command(cmd: Sequence[str], cwd: Path) -> None:
    rendered = " ".join(str(part) for part in cmd)
    print(f"$ (cd {cwd} && {rendered})")


def run_checked(
    cmd: Sequence[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> None:
    effective_cwd = cwd or REPO_ROOT
    print_command(cmd, effective_cwd)
    result = subprocess.run(
        list(cmd),
        cwd=effective_cwd,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def staged_runtime_python_changes(paths: RepoPaths) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--cached"],
        cwd=paths.repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [
        path
        for path in result.stdout.splitlines()
        if RUNTIME_CHANGE_PATTERN.match(path.strip())
    ]


def run_preflight(paths: RepoPaths) -> None:
    python = resolve_python(paths)
    run_checked([str(python), "scripts/release_preflight.py"], cwd=paths.repo_root)


def run_ci(
    paths: RepoPaths, *, quick: bool = False, full: bool = False, fix: bool = False
) -> None:
    python = resolve_python(paths)
    cmd = [str(python), "run_ci_checks.py"]
    if fix:
        cmd.append("--fix")
    if quick:
        cmd.append("--quick")
    if full:
        cmd.append("--full")
    run_checked(cmd, cwd=paths.repo_root)


def run_docs_check(paths: RepoPaths) -> None:
    python = resolve_python(paths)
    run_checked([str(python), "scripts/check_markdown_links.py"], cwd=paths.repo_root)
    run_checked([str(python), "scripts/check_markdown_style.py"], cwd=paths.repo_root)


def run_docs_consistency_guard(paths: RepoPaths) -> None:
    for relative_path in DOC_CONSISTENCY_PATHS:
        absolute_path = paths.repo_root / relative_path
        if absolute_path.is_dir():
            for child in absolute_path.rglob("*"):
                if not child.is_file():
                    continue
                check_file_for_tokens(child)
            continue
        if absolute_path.exists():
            check_file_for_tokens(absolute_path)


def check_file_for_tokens(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for token in FORBIDDEN_DOC_TOKENS:
        if token in text:
            raise SystemExit(f"forbidden token found in {path}: {token}")
    if re.search(r"(?<!POSTMARK_)FROM_EMAIL=", text):
        raise SystemExit(f"forbidden alias found in {path}: FROM_EMAIL=")


def run_newsletter_smoke(paths: RepoPaths) -> None:
    python = resolve_python(paths)
    run_checked(
        [str(python), "-c", NEWSLETTER_SMOKE],
        cwd=paths.repo_root,
        env=merged_env(MOCK_ENV),
    )


def run_web_smoke(paths: RepoPaths) -> None:
    python = resolve_python(paths)
    run_checked(
        [str(python), "-m", "pytest", "tests/test_web_api.py", "-q"],
        cwd=paths.repo_root,
        env=merged_env(MOCK_ENV),
    )


def run_scheduler_smoke(paths: RepoPaths) -> None:
    python = resolve_python(paths)
    run_checked(
        [
            str(python),
            "-m",
            "pytest",
            "tests/integration/test_schedule_execution.py",
            "tests/unit_tests/test_schedule_time_sync.py",
            "-q",
        ],
        cwd=paths.repo_root,
        env=merged_env({"MOCK_MODE": "true", "TESTING": "1"}),
    )


def run_ops_safety(paths: RepoPaths) -> None:
    python = resolve_python(paths)
    pytest_targets = [
        ["tests/unit_tests/test_config_import_side_effects.py", "-q"],
        ["tests/test_web_api.py", "-q"],
        ["tests/integration/test_schedule_execution.py", "-q"],
        ["tests/unit_tests/test_schedule_time_sync.py", "-q"],
        ["tests/contract/test_web_email_routes_contract.py", "-q"],
    ]
    for target_args in pytest_targets:
        extra_env = dict(MOCK_ENV)
        if "tests/integration/test_schedule_execution.py" in target_args:
            extra_env["RUN_INTEGRATION_TESTS"] = "1"
        run_checked(
            [str(python), "-m", "pytest", *target_args],
            cwd=paths.repo_root,
            env=merged_env(extra_env),
        )


def run_test_quick(paths: RepoPaths) -> None:
    run_preflight(paths)
    run_ci(paths, quick=True)
    changed_runtime_files = staged_runtime_python_changes(paths)
    if not changed_runtime_files:
        print("No staged runtime Python changes; skipping quick runtime pytest.")
        return
    python = resolve_python(paths)
    run_checked(
        [str(python), "-m", "pytest", "-m", "unit", "--maxfail=1", "--tb=short"],
        cwd=paths.repo_root,
        env=merged_env(MOCK_ENV),
    )


def run_test_full(paths: RepoPaths) -> None:
    run_preflight(paths)
    run_ci(paths, full=True)


def run_check(paths: RepoPaths, *, full: bool = False) -> None:
    command_doctor(argparse.Namespace())
    if full:
        run_test_full(paths)
    else:
        run_test_quick(paths)
    run_docs_check(paths)
    run_skills_check(paths)
    if full:
        run_ops_safety(paths)


def run_skills_check(paths: RepoPaths) -> None:
    run_docs_consistency_guard(paths)
    run_newsletter_smoke(paths)
    run_web_smoke(paths)
    run_scheduler_smoke(paths)


def build_run_command(
    paths: RepoPaths, target: str, target_args: Sequence[str]
) -> list[str]:
    python = resolve_python(paths)
    passthrough_args = list(target_args)
    if passthrough_args and passthrough_args[0] == "--":
        passthrough_args = passthrough_args[1:]
    if target == "web":
        if passthrough_args:
            raise SystemExit("run web does not accept extra arguments")
        return [str(python), "-m", "web.app"]
    if target == "worker":
        if passthrough_args:
            raise SystemExit("run worker does not accept extra arguments")
        return [str(python), "-m", "web.worker"]
    if target == "scheduler":
        if passthrough_args:
            raise SystemExit("run scheduler does not accept extra arguments")
        return [str(python), "-m", "web.schedule_runner"]
    if target == "newsletter":
        if not passthrough_args:
            passthrough_args = ["--help"]
        return [str(python), "-m", "newsletter", *passthrough_args]
    raise SystemExit(f"unsupported run target: {target}")


def install_requirements(paths: RepoPaths, python: Path) -> None:
    run_checked(
        [str(python), "-m", "pip", "install", "--upgrade", "pip"], cwd=paths.repo_root
    )
    run_checked(
        [str(python), "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=paths.repo_root,
    )
    run_checked(
        [str(python), "-m", "pip", "install", "-r", "requirements-dev.txt"],
        cwd=paths.repo_root,
    )


def command_bootstrap(_args: argparse.Namespace) -> None:
    paths = repo_paths()
    ensure_git_root(paths)
    base_python = Path(sys.executable)
    run_checked(
        [str(base_python), "-m", "venv", str(paths.default_venv_dir)],
        cwd=paths.repo_root,
    )
    python = venv_python(paths.default_venv_dir)
    install_requirements(paths, python)
    run_checked([str(python), "-m", "pre_commit", "install"], cwd=paths.repo_root)
    print(f"bootstrap complete: {python}")


def command_install(_args: argparse.Namespace) -> None:
    paths = repo_paths()
    ensure_git_root(paths)
    python = resolve_python(paths)
    install_requirements(paths, python)


def command_doctor(_args: argparse.Namespace) -> None:
    paths = repo_paths()
    ensure_git_root(paths)
    python = resolve_existing_venv_python(paths)
    if python is None:
        raise SystemExit(
            "virtualenv not found. Run 'python -m scripts.devtools.dev_entrypoint bootstrap' first."
        )
    print(f"repo_root={paths.repo_root}")
    print(f"python={python}")
    print(f"venv_dir={resolve_venv_dir(paths)}")


def command_print_python(_args: argparse.Namespace) -> None:
    paths = repo_paths()
    print(resolve_python(paths))


def command_print_venv(_args: argparse.Namespace) -> None:
    paths = repo_paths()
    print(resolve_venv_dir(paths))


def command_ci(args: argparse.Namespace) -> None:
    paths = repo_paths()
    ensure_git_root(paths)
    run_ci(paths, quick=args.quick, full=args.full, fix=args.fix)


def command_test(args: argparse.Namespace) -> None:
    paths = repo_paths()
    ensure_git_root(paths)
    if args.quick:
        run_test_quick(paths)
        return
    if args.full:
        run_test_full(paths)
        return
    raise SystemExit("select --quick or --full")


def command_docs_check(_args: argparse.Namespace) -> None:
    paths = repo_paths()
    ensure_git_root(paths)
    run_docs_check(paths)


def command_docs_consistency(_args: argparse.Namespace) -> None:
    paths = repo_paths()
    ensure_git_root(paths)
    run_docs_consistency_guard(paths)


def command_skills_check(_args: argparse.Namespace) -> None:
    paths = repo_paths()
    ensure_git_root(paths)
    run_skills_check(paths)


def command_ops_safety(_args: argparse.Namespace) -> None:
    paths = repo_paths()
    ensure_git_root(paths)
    run_ops_safety(paths)


def command_check(args: argparse.Namespace) -> None:
    paths = repo_paths()
    ensure_git_root(paths)
    run_check(paths, full=args.full)


def command_run(args: argparse.Namespace) -> None:
    paths = repo_paths()
    ensure_git_root(paths)
    cmd = build_run_command(paths, args.target, args.target_args)
    run_checked(cmd, cwd=paths.repo_root, env=merged_env())


def command_smoke(args: argparse.Namespace) -> None:
    paths = repo_paths()
    ensure_git_root(paths)
    if args.target == "newsletter":
        run_newsletter_smoke(paths)
        return
    if args.target == "web":
        run_web_smoke(paths)
        return
    if args.target == "scheduler":
        run_scheduler_smoke(paths)
        return
    raise SystemExit(f"unsupported smoke target: {args.target}")


def command_pre_commit_install(_args: argparse.Namespace) -> None:
    paths = repo_paths()
    ensure_git_root(paths)
    python = resolve_python(paths)
    run_checked([str(python), "-m", "pre_commit", "install"], cwd=paths.repo_root)


def command_pre_push_hook(_args: argparse.Namespace) -> None:
    paths = repo_paths()
    ensure_git_root(paths)
    installer = paths.repo_root / "scripts" / "devtools" / "setup_pre_push_hook.sh"
    shell = shutil.which("sh")
    if shell is None:
        raise SystemExit("sh is required to install the pre-push hook")
    run_checked([shell, str(installer)], cwd=paths.repo_root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Canonical developer entrypoint for local contributor workflows."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("bootstrap").set_defaults(func=command_bootstrap)
    subparsers.add_parser("install").set_defaults(func=command_install)
    subparsers.add_parser("doctor").set_defaults(func=command_doctor)
    subparsers.add_parser("print-python").set_defaults(func=command_print_python)
    subparsers.add_parser("print-venv").set_defaults(func=command_print_venv)

    ci_parser = subparsers.add_parser("ci")
    ci_parser.add_argument("--quick", action="store_true")
    ci_parser.add_argument("--full", action="store_true")
    ci_parser.add_argument("--fix", action="store_true")
    ci_parser.set_defaults(func=command_ci)

    test_parser = subparsers.add_parser("test")
    test_mode = test_parser.add_mutually_exclusive_group(required=True)
    test_mode.add_argument("--quick", action="store_true")
    test_mode.add_argument("--full", action="store_true")
    test_parser.set_defaults(func=command_test)

    subparsers.add_parser("docs-check").set_defaults(func=command_docs_check)
    subparsers.add_parser("docs-consistency").set_defaults(
        func=command_docs_consistency
    )
    subparsers.add_parser("skills-check").set_defaults(func=command_skills_check)
    subparsers.add_parser("ops-safety-check").set_defaults(func=command_ops_safety)

    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("--full", action="store_true")
    check_parser.set_defaults(func=command_check)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument(
        "target",
        choices=("web", "worker", "scheduler", "newsletter"),
    )
    run_parser.add_argument("target_args", nargs=argparse.REMAINDER)
    run_parser.set_defaults(func=command_run)

    smoke_parser = subparsers.add_parser("smoke")
    smoke_parser.add_argument(
        "target",
        choices=("newsletter", "web", "scheduler"),
    )
    smoke_parser.set_defaults(func=command_smoke)

    subparsers.add_parser("pre-commit-install").set_defaults(
        func=command_pre_commit_install
    )
    subparsers.add_parser("pre-push-hook").set_defaults(func=command_pre_push_hook)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
