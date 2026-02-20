#!/usr/bin/env python3
"""Launcher for kelimelik_deterministikstratejik_ajan_dawg_ (1).py with dependency preflight."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

SCRIPT_NAME = "kelimelik_deterministikstratejik_ajan_dawg_ (1).py"


def dependency_missing(pkg: str) -> bool:
    return importlib.util.find_spec(pkg) is None


def main() -> int:
    missing = [pkg for pkg in ["numpy"] if dependency_missing(pkg)]
    if missing:
        print("Missing required Python packages:", ", ".join(missing), file=sys.stderr)
        print("Install with: python -m pip install -r requirements.txt", file=sys.stderr)
        return 1

    script_path = Path(__file__).resolve().parent / SCRIPT_NAME
    return subprocess.call([sys.executable, str(script_path)])


if __name__ == "__main__":
    raise SystemExit(main())
