"""DEPRECATED — استَخدِم prepare_shamela_book.py بَدَلًا مِنه.

النِّسخَة الجَديدَة generic:

  python3 scripts/prepare_shamela_book.py --slug kashaf
"""

import sys
import subprocess
from pathlib import Path

print("⚠️  هذا السكربت مَنسوخ. الجَديد: prepare_shamela_book.py")
print()
print("سَأُشَغِّل الجَديد لَك بِـ slug=kashaf...")
print()
script = Path(__file__).parent / "prepare_shamela_book.py"
sys.exit(subprocess.call(
    [sys.executable, str(script), "--slug", "kashaf", *sys.argv[1:]]
))
