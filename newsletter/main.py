"""Deprecated FastAPI entrypoint kept for backwards compatibility.

Canonical web runtime is Flask (`web/app.py`).
Experimental FastAPI runtime moved to `apps.experimental.main`.
"""

from warnings import warn

try:
    from apps.experimental.main import app, main  # noqa: F401
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "FastAPI experimental runtime is not installed. "
        "Install optional dependencies with: "
        'pip install "newsletter-generator[api_experimental]"'
    ) from exc

warn(
    "newsletter.main is deprecated. Use apps.experimental.main instead.",
    DeprecationWarning,
    stacklevel=2,
)

if __name__ == "__main__":
    main()
