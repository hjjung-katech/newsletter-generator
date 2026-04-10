"""Unit tests for the platform adapter infrastructure."""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from newsletter_core.infrastructure.platform._frozen import (
    get_bundle_root,
    is_frozen,
    is_frozen_any,
)
from newsletter_core.infrastructure.platform._protocol import PlatformAdapter
from newsletter_core.infrastructure.platform._resolver import get_platform_adapter
from newsletter_core.infrastructure.platform._unix import UnixPlatformAdapter
from newsletter_core.infrastructure.platform._windows import WindowsPlatformAdapter

pytestmark = [pytest.mark.unit]


# ── Protocol conformance ─────────────────────────────────────────────


class TestPlatformProtocol:
    def test_windows_adapter_satisfies_protocol(self) -> None:
        adapter = WindowsPlatformAdapter()
        assert isinstance(adapter, PlatformAdapter)

    def test_unix_adapter_satisfies_protocol(self) -> None:
        adapter = UnixPlatformAdapter()
        assert isinstance(adapter, PlatformAdapter)


# ── Resolver ─────────────────────────────────────────────────────────


class TestPlatformResolver:
    def test_returns_windows_on_windows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(platform, "system", lambda: "Windows")
        adapter = get_platform_adapter()
        assert adapter.is_windows is True
        assert adapter.name == "Windows"
        assert adapter.is_queue_supported() is False

    def test_returns_unix_on_linux(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        adapter = get_platform_adapter()
        assert adapter.is_windows is False
        assert adapter.name == "Linux"
        assert adapter.is_queue_supported() is True

    def test_returns_unix_on_darwin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        adapter = get_platform_adapter()
        assert adapter.name == "Darwin"
        assert adapter.is_windows is False


# ── Windows adapter ──────────────────────────────────────────────────


class TestWindowsAdapter:
    def test_name_is_windows(self) -> None:
        assert WindowsPlatformAdapter().name == "Windows"

    def test_is_windows_true(self) -> None:
        assert WindowsPlatformAdapter().is_windows is True

    def test_queue_not_supported(self) -> None:
        assert WindowsPlatformAdapter().is_queue_supported() is False

    def test_signal_names_includes_sigbreak(self) -> None:
        names = WindowsPlatformAdapter().signal_names()
        assert "SIGINT" in names
        assert "SIGTERM" in names
        assert "SIGBREAK" in names

    def test_venv_path_uses_scripts(self, tmp_path: Path) -> None:
        result = WindowsPlatformAdapter().venv_python_path(tmp_path)
        assert result == tmp_path / "Scripts" / "python.exe"

    def test_configure_utf8_sets_env_vars(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.delenv("PYTHONIOENCODING", raising=False)
        monkeypatch.delenv("PYTHONUTF8", raising=False)

        # Mock stdout/stderr to have reconfigure
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()
        mock_stdout.reconfigure = MagicMock()
        mock_stderr.reconfigure = MagicMock()
        monkeypatch.setattr(sys, "stdout", mock_stdout)
        monkeypatch.setattr(sys, "stderr", mock_stderr)

        WindowsPlatformAdapter().configure_utf8_io()

        assert os.environ.get("PYTHONIOENCODING") == "utf-8"
        assert os.environ.get("PYTHONUTF8") == "1"
        mock_stdout.reconfigure.assert_called_once_with(
            encoding="utf-8", errors="replace"
        )
        mock_stderr.reconfigure.assert_called_once_with(
            encoding="utf-8", errors="replace"
        )

    def test_configure_utf8_noop_when_not_win32(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Safety guard: even if instantiated, does nothing on non-Windows."""
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.delenv("PYTHONIOENCODING", raising=False)
        monkeypatch.delenv("PYTHONUTF8", raising=False)

        WindowsPlatformAdapter().configure_utf8_io()

        assert "PYTHONIOENCODING" not in os.environ


# ── Unix adapter ─────────────────────────────────────────────────────


class TestUnixAdapter:
    def test_name_matches_system(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        assert UnixPlatformAdapter().name == "Darwin"

        monkeypatch.setattr(platform, "system", lambda: "Linux")
        assert UnixPlatformAdapter().name == "Linux"

    def test_is_windows_false(self) -> None:
        assert UnixPlatformAdapter().is_windows is False

    def test_queue_supported(self) -> None:
        assert UnixPlatformAdapter().is_queue_supported() is True

    def test_configure_utf8_noop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Calling configure_utf8_io on Unix must have no side-effects."""
        original_env = dict(os.environ)
        UnixPlatformAdapter().configure_utf8_io()
        # No new PYTHONIOENCODING should appear
        assert os.environ.get("PYTHONIOENCODING") == original_env.get(
            "PYTHONIOENCODING"
        )

    def test_signal_names_standard(self) -> None:
        names = UnixPlatformAdapter().signal_names()
        assert names == ["SIGINT", "SIGTERM"]

    def test_venv_path_uses_bin(self, tmp_path: Path) -> None:
        result = UnixPlatformAdapter().venv_python_path(tmp_path)
        assert result == tmp_path / "bin" / "python"


# ── Frozen detection ─────────────────────────────────────────────────


class TestFrozenDetection:
    def test_not_frozen_in_dev(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delattr(sys, "frozen", raising=False)
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)
        assert is_frozen() is False
        assert is_frozen_any() is False

    def test_frozen_with_meipass(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", "/tmp/bundle", raising=False)
        assert is_frozen() is True
        assert is_frozen_any() is True

    def test_frozen_without_meipass(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """is_frozen_any() returns True even without _MEIPASS."""
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)
        assert is_frozen() is False
        assert is_frozen_any() is True

    def test_bundle_root_returns_meipass_when_frozen(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        bundle_dir = str(tmp_path / "bundle")
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", bundle_dir, raising=False)
        assert get_bundle_root() == Path(bundle_dir)

    def test_bundle_root_returns_package_dir_when_dev(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delattr(sys, "frozen", raising=False)
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)
        root = get_bundle_root()
        # Should point to the _frozen.py parent directory
        assert root.is_dir()


# ── Signal registration ──────────────────────────────────────────────


class TestSignalHandlerRegistration:
    def test_posix_signals_registered_on_unix(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """setup_signal_handlers registers SIGINT and SIGTERM on Unix."""
        import signal as _signal

        from newsletter_core.infrastructure.platform._signal import (
            setup_signal_handlers,
        )

        registered: list[int] = []

        def _fake_signal(sig, handler):
            registered.append(int(sig))

        monkeypatch.setattr(_signal, "signal", _fake_signal)

        adapter = UnixPlatformAdapter()
        result = setup_signal_handlers(lambda s, f: None, lambda c: True, adapter)

        assert result is None  # no console handler on Unix
        assert int(_signal.SIGINT) in registered
        assert int(_signal.SIGTERM) in registered

    def test_no_sigbreak_on_unix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SIGBREAK must not be registered on Unix (it may not exist)."""
        import signal as _signal

        from newsletter_core.infrastructure.platform._signal import (
            setup_signal_handlers,
        )

        registered_names: list[str] = []

        def _fake_signal(sig, handler):
            try:
                registered_names.append(_signal.Signals(sig).name)
            except ValueError:
                registered_names.append(str(sig))

        monkeypatch.setattr(_signal, "signal", _fake_signal)

        adapter = UnixPlatformAdapter()
        setup_signal_handlers(lambda s, f: None, lambda c: True, adapter)

        assert "SIGBREAK" not in registered_names

    def test_windows_adapter_signal_names_include_sigbreak(self) -> None:
        names = WindowsPlatformAdapter().signal_names()
        assert "SIGBREAK" in names
        assert "SIGINT" in names
        assert "SIGTERM" in names

    def test_setup_signal_handlers_calls_windows_console_on_windows_adapter(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """On a Windows adapter, _register_windows_console_handler is invoked."""
        import newsletter_core.infrastructure.platform._signal as _sig_mod

        called: list[bool] = []

        def _fake_register(handler):
            called.append(True)
            return object()  # non-None sentinel

        monkeypatch.setattr(
            _sig_mod, "_register_windows_console_handler", _fake_register
        )

        import signal as _signal

        monkeypatch.setattr(_signal, "signal", lambda s, h: None)

        adapter = WindowsPlatformAdapter()
        result = _sig_mod.setup_signal_handlers(
            lambda s, f: None, lambda c: True, adapter
        )

        assert called, "_register_windows_console_handler should have been called"
        assert result is not None
