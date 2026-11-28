#!/usr/bin/env bash
# Regenerate every deliverable (batches 0-9) from source, then run the full check once.
# Deterministic: every item is rendered from a fixed RNG seed. Takes several minutes.
set -e; cd "$(dirname "$0")"
python3 sfx_fishing.py
python3 ambience_machine_room.py
python3 music.py
python3 music_batch1.py
python3 ambience_batch2.py
python3 ambience_batch3.py
python3 sfx_thunder.py
python3 hob_voice.py
python3 hob_sfx.py
python3 hands_sfx.py
python3 machines_sfx.py
python3 life_sfx.py
python3 music_batch8.py
python3 social_sfx.py
python3 check.py /workspace/house-audio ../reports/check_all.json | tee ../reports/check_all.txt
