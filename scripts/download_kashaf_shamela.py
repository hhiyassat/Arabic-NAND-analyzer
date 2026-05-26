"""DEPRECATED — استَخدِم download_shamela_book.py بَدَلًا مِنه.

النِّسخَة الجَديدَة generic — تَقبَل أَيّ كِتاب:

  python3 scripts/download_shamela_book.py --book-id 23627 --slug kashaf

أَو بِالرابِط:

  python3 scripts/download_shamela_book.py --url https://shamela.ws/book/23627
"""

import sys
import subprocess
from pathlib import Path

print("⚠️  هذا السكربت مَنسوخ. الجَديد: download_shamela_book.py")
print()
print("سَأُشَغِّل الجَديد لَك بِـ book-id=23627 slug=kashaf...")
print()
script = Path(__file__).parent / "download_shamela_book.py"
sys.exit(subprocess.call(
    [sys.executable, str(script), "--book-id", "23627", "--slug", "kashaf", *sys.argv[1:]]
))
