#!/usr/bin/env bash
# Regenerate batch 6 (machines, cooking, train, sweeper, house sfx; 7 loops + 22 one-shots) and verify everything.
set -e; cd "$(dirname "$0")"
python3 machines_sfx.py
python3 check.py /workspace/house-audio ../reports/check_batch6.json | tee ../reports/check_batch6.txt
