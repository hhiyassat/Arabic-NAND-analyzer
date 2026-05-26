#!/bin/bash
# run_i3rab.sh — تشغيل محرّك الإعراب بسهولة (Mac/Linux)
#
# الاستخدام:
#   ./run_i3rab.sh "إِنَّ اللَّهَ غَفُورٌ رَحِيمٌ"
#   ./run_i3rab.sh --csv my_sentences.csv --csv-out result.csv

cd "$(dirname "$0")"
python3 i3rab.py "$@"
