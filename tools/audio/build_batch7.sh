#!/usr/bin/env bash
# Regenerate batch 7 (books/creatures/life sfx, event jingles, ui) and verify everything.
set -e; cd "$(dirname "$0")"
python3 life_sfx.py
python3 check.py /workspace/house-audio ../reports/check_batch7.json | tee ../reports/check_batch7.txt
