#!/bin/bash
# run_morph.sh — تشغيل المحلّل الصرفي بسهولة (Mac/Linux)
#
# الاستخدام:
#   ./run_morph.sh "كَتَبَ"
#   ./run_morph.sh --file my_text.txt
#   ./run_morph.sh --csv words.csv --csv-out result.csv

cd "$(dirname "$0")"
python3 morph.py "$@"
