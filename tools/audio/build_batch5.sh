#!/usr/bin/env bash
# Regenerate batch 5 (hands/making/building/gathering sfx) and verify everything.
set -e; cd "$(dirname "$0")"
python3 hands_sfx.py
python3 check.py /workspace/house-audio ../reports/check_batch5.json | tee ../reports/check_batch5.txt
