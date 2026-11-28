#!/bin/sh
# The one gate (SPEC-v4.0.5 §9.1): every self-check, the art and sound, and the view. Stops at the first failure.
# RUNNING.md's "run the self-checks" means this. About 15 minutes. Scratch goes to $PET_SCRATCH (else the system's temp).
set -e
cd "$(dirname "$0")"
step() { printf '\n== %s\n' "$*"; }
step "engine.check, then every engine/check_*.py"
uv run python -m engine.check
step "art and sound (validate.py)"
uv run --with pillow python view/assets/own/src/validate.py
step "the view: types, build, voice and talk"
(cd view && npx tsc --noEmit && npm run build)
node view/check-voice.ts
node view/check-talk.ts
node view/check-family.ts
node view/check-spirit.ts
node view/check-work.ts
step "no fakes in the built page"
if grep -l "fake" view/dist/assets/*.js; then echo "the production bundle carries the DEV fakes"; exit 1; fi
printf "\ncheck.sh: all passed\n"
