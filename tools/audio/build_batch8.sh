#!/usr/bin/env bash
# Regenerate batch 8 (11 place/mood music loops; attic from batch 0 kept as is) and verify everything.
set -e; cd "$(dirname "$0")"
python3 music_batch8.py
python3 check.py /workspace/house-audio ../reports/check_batch8.json | tee ../reports/check_batch8.txt
