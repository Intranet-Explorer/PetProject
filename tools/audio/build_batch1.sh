#!/usr/bin/env bash
# Regenerate batch 1 (time-of-day music + dawn/dusk jingles) and verify the whole tree.
set -e; cd "$(dirname "$0")"
python3 music_batch1.py
python3 check.py /workspace/house-audio ../reports/check_batch1.json | tee ../reports/check_batch1.txt
