"""conftest.py — تَجهيز sys.path لِـ pytest."""

import sys
from pathlib import Path

# نُضيف src لِلـ path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
