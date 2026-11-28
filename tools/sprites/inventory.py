#!/usr/bin/env python3
"""Cut the existing PixelLab grids and build an offline keep-list review page.

Requires Python 3.11+ and Pillow. Run from any directory:
  python tools/sprites/inventory.py [--incoming /path/to/assets-incoming]
Never imports the generation helpers or reads credentials.
"""
import argparse
import hashlib
import html
import json
import re
import tomllib
from pathlib import Path

from PIL import Image


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def inventory(incoming):
    source = incoming / "pixellab"
    manifest_bytes = (source / "sheets.toml").read_bytes()
    manifest = tomllib.loads(manifest_bytes.decode())
    sheets, directories = [], []
    # Validate every grid before writing any crops; never pad an out-of-bounds cell.
    for key, spec in manifest.items():
        if "file" not in spec:
            directories.append({"name": key, **spec})
            continue
        size, cols, names = spec["cell"], spec["columns"], spec["names"]
        misses = set(spec.get("miss", []))
        if size <= 0 or cols <= 0 or not names or not misses <= set(range(len(names))):
            raise ValueError(f"Invalid grid specification: {key}")
        with Image.open(source / spec["file"]) as im:
            expected = (size * cols, ((len(names) + cols - 1) // cols) * size)
            if im.size != expected:
                raise ValueError(f"{key}: {im.size} does not match {expected}")
        sheets.append({"name": key, **spec, "cells": []})
    for sheet in sheets:
        key, size, cols = sheet["name"], sheet["cell"], sheet["columns"]
        target = source / "cells" / key
        target.mkdir(parents=True, exist_ok=True)
        with Image.open(source / sheet["file"]) as im:
            for index, name in enumerate(sheet["names"]):
                if index in sheet.get("miss", []):
                    continue
                filename = f"{index:02d}-{slug(name)}.png"
                x, y = index % cols * size, index // cols * size
                crop = im.crop((x, y, x + size, y + size))
                crop.save(target / filename)
                sheet["cells"].append({"sheet": key, "index": index, "name": name,
                    "size": [size, size], "rect": [x, y, size, size],
                    "file": f"pixellab/cells/{key}/{filename}"})
        print(f"{key}: {len(sheet['cells'])} cut, {len(sheet.get('miss', []))} skipped")
    result = {"version": 1, "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
              "sheets": sheets, "directories": directories}
    (source / "cells" / "inventory.json").write_text(json.dumps(result, indent=2) + "\n")
    preview = incoming / "_previews" / "pixellab-all.html"
    preview.parent.mkdir(parents=True, exist_ok=True)
    preview.write_text(render(result))
    print(f"Total: {sum(len(s['cells']) for s in sheets)} cells across {len(sheets)} grids")
    print(preview)


def render(data):
    sections = []
    for sheet in data["sheets"]:
        cards = []
        for cell in sheet["cells"]:
            size = cell["size"][0]
            ident = f"{cell['sheet']}:{cell['index']}"
            pictures = ''.join(f'<figure><img src="../{html.escape(cell["file"])}" width="{size * scale}" height="{size * scale}" alt="{html.escape(cell["name"], quote=True)}"><figcaption>{scale}×</figcaption></figure>' for scale in (1, 2, 4))
            cards.append(f'<article data-search="{html.escape(ident + " " + cell["name"], quote=True)}"><label><input type="checkbox" data-id="{ident}"> Keep <b>#{cell["index"]} · {html.escape(cell["name"])}</b></label><small>{cell["sheet"]} · {size} × {size} px</small><div class="pictures">{pictures}</div></article>')
        skipped = ', '.join(map(str, sheet.get('miss', []))) or 'none'
        sections.append(f'<section id="{sheet["name"]}"><h2>{sheet["name"]} <span>{len(sheet["cells"])} cells · skipped: {skipped}</span></h2><p>{html.escape(sheet.get("note", ""))}</p><div class="grid">{"".join(cards)}</div></section>')
    links = ' '.join(f'<a href="#{s["name"]}">{s["name"]}</a>' for s in data['sheets'])
    directories = ''.join(f'<li><b>{html.escape(d["name"])}</b>: {html.escape(d.get("note", ""))}</li>' for d in data['directories'])
    payload = json.dumps(data).replace('<', '\\u003c')
    return '''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PixelLab · all cells</title>
<style>
:root{color-scheme:dark;font:15px system-ui;background:#181b20;color:#e9edf3}body{margin:0;padding:24px}h1{margin:0 0 8px}header{position:sticky;top:0;background:#181b20f5;z-index:2;padding:12px 0;border-bottom:1px solid #48515c}nav{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}a{color:#9bd6bc}button,input,select{font:inherit}button,select,input[type=search]{padding:7px;background:#2b333d;color:inherit;border:1px solid #607080;border-radius:5px}button{cursor:pointer}input[type=checkbox]{width:19px;height:19px;vertical-align:middle;accent-color:#9bd6bc}h2 span,small,figcaption{color:#b4c0cb;font-size:12px;font-weight:normal}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}article{border:1px solid #48515c;border-radius:6px;padding:12px;background:#20262e}article:has(input:checked){border-color:#9bd6bc}article small{display:block;margin:8px 0}.pictures{display:flex;align-items:flex-end;justify-content:space-around;gap:10px;min-height:100px;overflow:auto}figure{margin:0;text-align:center}img{display:block;image-rendering:pixelated;background-color:var(--matte,#68717c);background-image:linear-gradient(45deg,#ffffff18 25%,transparent 25%),linear-gradient(-45deg,#ffffff18 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#ffffff18 75%),linear-gradient(-45deg,transparent 75%,#ffffff18 75%);background-size:8px 8px;background-position:0 0,0 4px,4px -4px,-4px 0}section{scroll-margin-top:190px;margin-top:30px}textarea{width:100%;height:180px;background:#10151a;color:#c9e9d8}#status{margin-left:8px}footer{margin-top:32px}
</style>
<h1>PixelLab · all cells</h1><p>__TOTAL__ original cells, 17 sheets. Zero-based indices, row-major order. Miss cells are omitted. Images retain their original pixels and transparency.</p>
<header><input id="search" type="search" aria-label="Filter cells" placeholder="Filter sheet, index or name"> <button id="all">Keep all visible</button> <button id="none">Clear visible</button> <button id="export">Download keep-list JSON</button> <label>Backdrop <select id="matte"><option value="#68717c">Grey</option><option value="#faf5e6">Light</option><option value="#111820">Dark</option></select></label><output id="status" aria-live="polite"></output><nav>__LINKS__</nav></header>
<main>__SECTIONS__</main>
<footer><h2>Keep-list JSON</h2><p>Checkboxes update this JSON immediately and save locally when browser storage is available. Download the keep-list to share your choices. No cells are selected by default.</p><textarea id="json" readonly aria-label="Keep-list JSON"></textarea><p id="storage" role="status"></p><details><summary>Other manifest entries (animation directories, no grid specification)</summary><ul>__DIRECTORIES__</ul></details></footer>
<script id="inventory" type="application/json">__DATA__</script>
<script>
const inventory=JSON.parse(document.getElementById('inventory').textContent);
const cells=inventory.sheets.flatMap(s=>s.cells), boxes=[...document.querySelectorAll('[data-id]')];
const storageKey='petproject.pixellab.keep.v1.'+inventory.manifest_sha256;
let saved=[];
try {saved=JSON.parse(localStorage.getItem(storageKey)||'[]');if(!Array.isArray(saved)) saved=[];} catch {document.getElementById('storage').textContent='Browser storage unavailable; download JSON to keep your choices.';}
const keep=new Set(saved);boxes.forEach(b=>b.checked=keep.has(b.dataset.id));
function update(){
 const selected=new Set(boxes.filter(b=>b.checked).map(b=>b.dataset.id));
 const result={version:1,manifest_sha256:inventory.manifest_sha256,keep:cells.filter(c=>selected.has(c.sheet+':'+c.index))};
 document.getElementById('json').value=JSON.stringify(result,null,2)+'\\n';
 document.getElementById('status').textContent=selected.size+' / '+cells.length+' kept';
 try {localStorage.setItem(storageKey,JSON.stringify([...selected]));} catch {}
}
boxes.forEach(b=>b.addEventListener('change',update));
document.getElementById('search').addEventListener('input',e=>{const q=e.target.value.toLowerCase();document.querySelectorAll('article').forEach(c=>c.hidden=!c.dataset.search.toLowerCase().includes(q));});
for(const [id,value] of [['all',true],['none',false]]) document.getElementById(id).onclick=()=>{boxes.filter(b=>!b.closest('article').hidden).forEach(b=>b.checked=value);update();};
document.getElementById('matte').onchange=e=>document.documentElement.style.setProperty('--matte',e.target.value);
document.getElementById('export').onclick=()=>{const url=URL.createObjectURL(new Blob([document.getElementById('json').value],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='pixellab-keep-list.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
update();
</script></html>'''.replace('__TOTAL__', str(sum(len(s['cells']) for s in data['sheets']))).replace('__LINKS__', links).replace('__SECTIONS__', ''.join(sections)).replace('__DIRECTORIES__', directories).replace('__DATA__', payload)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--incoming', type=Path, default=Path(__file__).resolve().parents[2] / 'assets-incoming')
    inventory(parser.parse_args().incoming)
