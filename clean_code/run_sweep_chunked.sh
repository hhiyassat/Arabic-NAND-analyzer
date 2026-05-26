#!/bin/bash
# Run sweep in chunks of 200 verses, append to sweep_v3.jsonl
cd "$(dirname "$0")"
START=${1:-0}
END=${2:-6236}
STEP=200
for ((s=$START; s<$END; s+=$STEP)); do
    e=$((s+STEP))
    if [ $e -gt $END ]; then e=$END; fi
    echo "=== Chunk $s..$e ==="
    timeout 40 python3 sweep_quran_all.py --start-idx $s --end-idx $e --save-jsonl sweep_v3.jsonl --report-only 2>&1 | tail -3
done
