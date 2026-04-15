"""
Task tracking directory containing todo.md and lessons.md.

This file prevents Python from treating tasks/ as a namespace package that
shadows web/tasks.py when the repo root is in sys.path during test collection.
"""
import importlib.util
import os
import sys

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_web_dir = os.path.join(_repo_root, "web")
_tasks_path = os.path.join(_web_dir, "tasks.py")

if _web_dir not in sys.path:
    sys.path.insert(0, _web_dir)

_spec = importlib.util.spec_from_file_location("tasks", _tasks_path)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["tasks"] = _mod  # replace this package with web/tasks.py
_spec.loader.exec_module(_mod)
