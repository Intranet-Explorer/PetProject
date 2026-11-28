#!/usr/bin/env bash
# Regenerate batch 2 room ambiences (+ machine_room with its batch-2 tick layer) and verify everything.
set -e; cd "$(dirname "$0")"
python3 ambience_machine_room.py
python3 ambience_batch2.py
python3 check.py /workspace/house-audio ../reports/check_batch2.json | tee ../reports/check_batch2.txt
