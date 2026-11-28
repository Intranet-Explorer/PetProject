# PixelLab sprite tools

Run with Python 3.11+ and Pillow. Work from the `sprites` checkout; its
`assets-incoming` symlink supplies the source art. Neither tool calls PixelLab or
reads credentials.

- `inventory.py` cuts non-miss cells from `assets-incoming/pixellab/sheets.toml`
  and builds the ignored visual keep-list page.
- `import_pixellab.py` imports the 184 approved mappings recorded in
  `pixellab-approved.json`. Pass `--output /path/to/stage` to stage the result;
  the default writes `view/assets/` in the current tool's checkout. Re-running
  it produces the same output from the same sources.

The visual keep-list is not a mapping gate. The user approved every mapping
row, including proposals outside that visual pass. Source sheets remain
unchanged under `view/assets/own/pixellab/`; their ordered names, misses, used
indices and SHA-256 hashes are in `own/pixellab/src/names.json`.

The renderer discards pixels outside the fixed `parts.json` palette. Approved
part cells therefore have separate palette-coded copies fitted to the existing
attachment bounds. Fifteen existing part names use those 16 px copies and keep
their old native 24/32 px art. Five new names with cells have adapted 16 px art
and explicitly padded (unscaled) 24/32 px stand-ins. Their definitions, plus six
new names without cells, live in `parts.json:v5_pending.thing`: the current
engine requires active `thing` names to match the root effect registry. The
v5.1 lead must update that registry before moving these definitions into
`thing`. The importer never changes root configuration or engine/view code.

`view/assets/pixellab.json` is the lead's list: 67 kind decisions, 30 part
statuses, and 87 namespaced fixture candidates. No existing room layout or
fixture state is replaced. The six kinds marked `generate` keep their previous
sprites. `/art/preview.html#pixellab` shows the imported kinds, adapted parts,
and fixture candidates; `#kinds` includes the full colour grid at source sizes.

`view/assets/pixellab-gaps.json` and the ignored
`assets-incoming/pixellab/v5/generation-review.html` describe step 4's proposed
work. Generation is still awaiting review. The design does not enumerate its
roughly 250 future grammar-derived catalog items; do not invent a 300-sprite
batch in their place. Step 5's `invent.py` remains after that review gate.

Validation performed for this import:

- Every source sheet copied byte-for-byte; all rectangles and palette-coded
  part pixels checked; reimport produces no file differences.
- `python -B -m engine.check_parts` and `python -B -m engine.check_design`.
- `python -B view/assets/own/src/validate.py` currently stops at missing release
  audio, as it did before the import.
- `python -B -m engine.check` currently cannot reach its websocket server: the
  checkout has no built view (`engine.server`: “build the view first”). Building
  outside the allowed asset/tool paths is left to the lead.
