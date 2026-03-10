import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_ENTRYPOINT = "scripts.devtools.dev_entrypoint"


def _read_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _target_body(makefile_text: str, target: str) -> str:
    pattern = re.compile(
        rf"^{re.escape(target)}:.*\n((?:\t[^\n]*\n)+)",
        re.MULTILINE,
    )
    match = pattern.search(makefile_text)
    assert match is not None, f"target not found: {target}"
    return match.group(1)


def test_makefile_routes_contributor_targets_through_dev_entrypoint():
    makefile = _read_text("Makefile")
    expected_targets = {
        "bootstrap": "$(DEV_ENTRYPOINT) bootstrap",
        "doctor": "$(DEV_ENTRYPOINT) doctor",
        "print-python": "$(DEV_ENTRYPOINT) print-python",
        "print-venv": "$(DEV_ENTRYPOINT) print-venv",
        "check": "$(DEV_ENTRYPOINT) check",
        "check-full": "$(DEV_ENTRYPOINT) check --full",
        "install": "$(DEV_ENTRYPOINT) install",
        "test-quick": "$(DEV_ENTRYPOINT) test --quick",
        "test-full": "$(DEV_ENTRYPOINT) test --full",
        "ci-check": "$(DEV_ENTRYPOINT) ci",
        "ci-fix": "$(DEV_ENTRYPOINT) ci --fix",
        "ci-full": "$(DEV_ENTRYPOINT) ci --full",
        "skill-ci-gate": "$(DEV_ENTRYPOINT) ci --fix --full",
        "skill-docs-and-config-consistency": "$(DEV_ENTRYPOINT) docs-consistency",
        "skill-newsletter-smoke": "$(DEV_ENTRYPOINT) smoke newsletter",
        "skill-web-smoke": "$(DEV_ENTRYPOINT) smoke web",
        "skill-scheduler-debug": "$(DEV_ENTRYPOINT) smoke scheduler",
        "docs-check": "$(DEV_ENTRYPOINT) docs-check",
        "ops-safety-check": "$(DEV_ENTRYPOINT) ops-safety-check",
        "pre-commit": "$(DEV_ENTRYPOINT) pre-commit-install",
        "pre-push-hook": "$(DEV_ENTRYPOINT) pre-push-hook",
    }

    for target, expected_command in expected_targets.items():
        assert expected_command in _target_body(makefile, target)


def test_makefile_removed_fixed_path_expected_cwd_and_python3_hardcoding():
    makefile = _read_text("Makefile")
    assert "EXPECTED_CWD" not in makefile
    assert "python3" not in makefile
    assert "/Users/hojungjung/development/newsletter-generator" not in makefile


def test_shell_wrapper_and_help_text_use_dev_entrypoint_contract():
    pre_push_hook = _read_text("scripts/devtools/hooks/pre-push")
    setup_hook = _read_text("scripts/devtools/setup_pre_push_hook.sh")
    run_ci_checks = _read_text("run_ci_checks.py")

    assert f"python -m {DEV_ENTRYPOINT} check" in pre_push_hook
    assert "python3" not in pre_push_hook
    assert "#!/bin/sh" in setup_hook
    assert "BASH_SOURCE" not in setup_hook
    assert f"python -m {DEV_ENTRYPOINT} ci --quick" in run_ci_checks
    assert f"python -m {DEV_ENTRYPOINT} check --full" in run_ci_checks


def test_active_docs_point_to_python_entrypoint_and_avoid_fixed_clone_paths():
    support_policy = _read_text("docs/reference/support-policy.md")
    readme = _read_text("README.md")
    installation = _read_text("docs/setup/INSTALLATION.md")
    quick_start = _read_text("docs/setup/QUICK_START_GUIDE.md")
    local_setup = _read_text("docs/setup/LOCAL_SETUP.md")
    local_ci = _read_text("docs/dev/LOCAL_CI_GUIDE.md")
    ci_cd = _read_text("docs/dev/CI_CD_GUIDE.md")

    for text in (
        support_policy,
        readme,
        installation,
        quick_start,
        local_setup,
        local_ci,
        ci_cd,
    ):
        assert f"python -m {DEV_ENTRYPOINT}" in text
        assert "/Users/hojungjung/development/newsletter-generator" not in text

    assert "thin wrapper" in readme
    assert "wrapper" in local_ci
    assert "wrapper" in ci_cd
