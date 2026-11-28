#!/usr/bin/env bash
# Regenerate batch 9 (needs, getting along, conflict, the visitor sfx; argue/scuffle 4 s loops) and verify everything.
set -e; cd "$(dirname "$0")"
python3 social_sfx.py
python3 check.py /workspace/house-audio ../reports/check_batch9.json | tee ../reports/check_batch9.txt
