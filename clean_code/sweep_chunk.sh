#!/bin/bash
# sweep_chunk.sh — يُشَغِّل sweep لِنِطاق مَع حِفظ JSONL لِإِمكان الِاستِئناف.
# الِاستِخدام:
#   ./sweep_chunk.sh START END
#   مَثَلًا: ./sweep_chunk.sh 1:1 2:50

START="$1"
END="$2"
JSONL="${3:-sweep_results.jsonl}"

cd "$(dirname "$0")"
python3 sweep_quran_all.py \
    --start "$START" \
    --end "$END" \
    --save-jsonl "$JSONL" \
    --resume-from "$JSONL" \
    --report-only
