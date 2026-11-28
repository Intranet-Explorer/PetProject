#!/usr/bin/env bash
# Regenerate batch 3 (outdoor/weather ambience + thunder sfx) and verify everything.
set -e; cd "$(dirname "$0")"
python3 ambience_batch3.py
python3 sfx_thunder.py
python3 check.py /workspace/house-audio ../reports/check_batch3.json | tee ../reports/check_batch3.txt
