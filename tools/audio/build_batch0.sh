#!/usr/bin/env bash
# Regenerate batch 0 of 'the house' audio and verify. Deterministic (seeded RNG in synth.py).
set -e; cd "$(dirname "$0")"
python3 sfx_fishing.py
python3 ambience_machine_room.py
python3 music.py
python3 check.py /workspace/house-audio ../reports/check_batch0.json | tee ../reports/check_batch0.txt
