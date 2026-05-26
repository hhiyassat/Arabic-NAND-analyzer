#!/usr/bin/env python3
"""Launcher — run from ``hussein/`` without ``cd src``."""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from architecture_test.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
