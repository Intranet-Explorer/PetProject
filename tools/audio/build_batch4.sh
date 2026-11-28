#!/usr/bin/env bash
# Regenerate batch 4 (hob body + voice sfx, voice review demos) and verify everything.
set -e; cd "$(dirname "$0")"
python3 hob_voice.py          # reports/voice_demo_*.wav (review only, not deliverables)
python3 hob_sfx.py
python3 check.py /workspace/house-audio ../reports/check_batch4.json | tee ../reports/check_batch4.txt
