#!/usr/bin/env python3
"""Import approved PixelLab mappings without any network or generation calls.

Requires Python 3.11+ and Pillow. Use --output to stage changes for review.
The approved snapshot is committed beside this script; source PNGs stay ignored.
"""
import argparse
import copy
import hashlib
import json
import re
import shutil
import tomllib
from pathlib import Path
from PIL import Image


def read(path):
    return json.loads(path.read_text())


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.name == 'sprites.json':
        text='{\n'+',\n'.join(' '+json.dumps(k)+': '+json.dumps(v) for k,v in data.items())+'\n}'
    else:
        text=json.dumps(data,indent=1)
        if path.name=='parts.json':
            text=re.sub(r'\[\s+((?:(?:-?[\d.]+|"[^"\n]*"),\s+)*(?:-?[\d.]+|"[^"\n]*"))\s+\]',lambda m:'['+re.sub(r',\s+',', ',m.group(1))+']',text)
    path.write_text(text+'\n')


def import_art(repo, incoming, output, approved):
    source=incoming/'pixellab'; art=repo/'view/assets'; dest=output/'view/assets'
    manifest=tomllib.loads((source/'sheets.toml').read_text())
    assert hashlib.sha256((source/'sheets.toml').read_bytes()).hexdigest()==approved['manifest_sha256']
    sprites,kinds,lib=(read(art/f) for f in ('sprites.json','kinds.json','parts.json'))
    lib['v5_pending']={'about':'Approved v5.1 definitions. Move into thing only when the root effect registry accepts their names; missing native sizes remain pending.','thing':{}}
    for row in approved['parts']:
        if approved['original_parts'][row['part']] is None:lib['thing'].pop(row['part'],None)
    inv=read(source/'cells/inventory.json')
    cells={f"{c['sheet']}:{c['index']}":c for sheet in inv['sheets'] for c in sheet['cells']}
    imports={r['cell'] for g in ('kinds','parts','fixtures') for r in approved[g] if r['cell']!='generate'}
    assert imports <= cells.keys()
    names={}
    for sheet in sorted({cells[c]['sheet'] for c in imports}):
        spec=manifest[sheet];target=dest/'own/pixellab'/spec['file'];target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source/spec['file'],target)
        names[sheet]={**spec,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'used':[cells[c]['index'] for c in sorted(imports) if cells[c]['sheet']==sheet]}
    info={'approval':{'rows':184,'draft_sha256':approved['draft_sha256']},'kinds':[],'parts':[],'fixtures':[]}
    def entry(cid):
        c=cells[cid];return {'pack':'own','file':'pixellab/'+manifest[c['sheet']]['file'],'rect':c['rect']}
    for row in approved['kinds']:
        name,cid=row['kind'],row['cell'];record={k:row[k] for k in ('kind','cell','status','note')}
        if cid!='generate':
            sid='kind.pixellab.'+name;s=entry(cid);s['tint']='none'
            w,h=s['rect'][2:];s['anchor']=[(w-16)//2,h-16+(24 if kinds[name]['wall'] else 0)]
            sprites[sid]=s;kinds[name]['sprite']=sid
            # Existing state variants (notably the bare plant pot) still work.
            for old_id,old in list(sprites.items()):
                if old_id.startswith(row['current_sprite']+'.'):
                    sprites[sid+old_id[len(row['current_sprite']):]]=copy.deepcopy(old)
        record['sprite']=kinds[name]['sprite'];info['kinds'].append(record)
    for row in approved['fixtures']:
        sid='fix.pixellab.'+row['suggested_name'];s=entry(row['cell']);w,h=s['rect'][2:]
        s['anchor']=[(w-16)//2,h-16];sprites[sid]=s
        info['fixtures'].append({**{k:v for k,v in row.items() if k not in ('sprite','default_approved')},'sprite':sid})
    # The renderer recognizes only these palette entries. Unknown RGBs disappear.
    palette=[tuple(bytes.fromhex(h)) for value in lib['palette'].values() for h in ([value] if isinstance(value,str) else value)]
    def quantize(im):
        im=im.convert('RGBA');out=Image.new('RGBA',im.size)
        out.putdata([(*min(palette,key=lambda q:sum((q[i]-p[i])**2 for i in range(3))),p[3]) if p[3] else (0,0,0,0) for p in im.getdata()])
        return out
    sheets={n:Image.new('RGBA',(8*n,3*n)) for n in (16,24,32)}
    part_names=[]
    for row in approved['parts']:
        name,cid=row['part'],row['cell'];original=copy.deepcopy(approved['original_parts'][name]);draft=json.loads(row['draft_entry_json'])
        if cid=='generate':
            if original is None:lib['v5_pending']['thing'][name]={k:v for k,v in draft.items() if k!='px'}
            info['parts'].append({'part':name,'cell':cid,'status':'generation_pending','fallback':'existing art' if original else 'undrawn'})
            continue
        n=len(part_names);part_names.append(name);c=cells[cid]
        with Image.open(source/manifest[c['sheet']]['file']) as im:
            x,y,w,h=c['rect'];crop=im.convert('RGBA').crop((x,y,x+w,y+h));crop=crop.crop(crop.getbbox())
        # Keep existing attachment geometry and extents so all existing recipes fit.
        # Raw, approved source art remains in the copied parts16.png for provenance.
        if original:
            ref=copy.deepcopy(original['px']['16'])
            with Image.open(art/ref['file']) as im:
                x,y,w,h=ref['rect'];bounds=im.crop((x,y,x+w,y+h)).getbbox()
        elif draft['role']=='base':
            ref=copy.deepcopy(approved['box_geometry']['px']['16'])
            with Image.open(art/ref['file']) as im:
                x,y,w,h=ref['rect'];bounds=im.crop((x,y,x+w,y+h)).getbbox()
        else:
            ref={'pin':[7,12]};bounds=(4,7,12,15)
        l,t,r,b=bounds
        stamp=Image.new('RGBA',(16,16));stamp.paste(quantize(crop.resize((r-l,b-t),Image.Resampling.NEAREST)),(l,t))
        part=original or {k:v for k,v in draft.items() if k!='px'};part.setdefault('px',{})
        for size in (16,24,32):
            if size!=16 and original:
                continue  # retain native existing larger-size art; do not invent a 24 px redraw
            offset=(size-16)//2;pic=Image.new('RGBA',(size,size));pic.paste(stamp,(offset,offset))
            sheets[size].paste(pic,((n%8)*size,(n//8)*size))
            px={'file':f'own/pixellab/parts-compatible{size}.png','rect':[(n%8)*size,(n//8)*size,size,size]}
            for key in ('pin','at'):
                if key in ref:
                    px[key]=([q+offset for q in ref[key]] if key=='pin' else {a:[q+offset for q in point] for a,point in ref[key].items()})
            part['px'][str(size)]=px
        target=lib['thing'] if original else lib['v5_pending']['thing']
        target[name]=part
        for size,px in part['px'].items():
            sprites[f'part.pixellab.{name}.{size}']={'pack':'own','file':px['file'].removeprefix('own/'),'rect':px['rect'],'tint':'none'}
        info['parts'].append({'part':name,'cell':cid,'status':'imported16','active':bool(original),'source_file':entry(cid)['file'],
            'adapter':'palette converted and fitted to existing attachment bounds' if original else 'palette converted; 24/32 px are padded 16 px stand-ins',
            'native24_pending':True,'larger_sizes':'existing native art' if original else 'padded stand-ins'})
    for size,im in sheets.items():im.save(dest/f'own/pixellab/parts-compatible{size}.png')
    names['parts-compatible']={'names':part_names,'columns':8,'sizes':[16,24,32],'note':'16: all listed parts; 24/32: only new parts without existing native art, padded at 1x. Other slots transparent.'}
    write(dest/'own/pixellab/src/names.json',names)
    write(dest/'pixellab.json',info)
    write(dest/'kinds.json',kinds);write(dest/'sprites.json',sprites);write(dest/'parts.json',lib)
    credits=(art/'third_party/CREDITS.md').read_text()
    marker='## PixelLab approved v5 art'
    if marker not in credits:
        credits+='\n'+marker+'\n\n`../own/pixellab/` contains sheets generated for this project with [PixelLab](https://www.pixellab.ai)\nusing `generate-with-style-v2` in October 2026, with Ninja Adventure items as the original style references.\nUsed under PixelLab’s terms of service, as with the existing PixelLab art above.\n`../own/pixellab/src/names.json` records source names, cell order, misses, hashes and used indices.\nSource sheets are unchanged. `parts-compatible*.png` adapts approved cells to the compositor palette and\nattachment bounds. New part names are in `parts.json` under `v5_pending` until the v5.1\neffect registry accepts them. 24/32 px entries for new parts are padded 16 px stand-ins pending native-size review.\n`../pixellab.json` lists the approved kinds, parts, and 87 fixture candidates for the lead.\n'
    if 'New part names are in `parts.json`' not in credits:
        credits+='\nNew part names are in `parts.json` under `v5_pending` until the v5.1 effect registry accepts them.\n'
    (dest/'third_party').mkdir(exist_ok=True);(dest/'third_party/CREDITS.md').write_text(credits)
    preview=(art/'preview.html').read_text()
    preview=preview.replace('const [packs, sprites, kinds] = await Promise.all(["packs.json", "sprites.json", "kinds.json"].map(J));','const [packs, sprites, kinds, pixellab] = await Promise.all(["packs.json", "sprites.json", "kinds.json", "pixellab.json"].map(J));')
    preview=preview.replace('cols = Object.keys(COLOURS), cw = 16 * K + 6;', 'cols = Object.keys(COLOURS), cw = Math.max(...names.map((n) => Math.max(...sprites[kinds[n].sprite].rect.slice(2)))) * K + 6;')
    block='''// Approved PixelLab import: source-sized hero sprites, including explicit legacy fallbacks.
if (!want || want === "kinds" || want === "pixellab") {
  const to = section("PixelLab kinds · approved sources (pending generation keeps the previous sprite)", "grid sand");
  for (const row of pixellab.kinds) figure(to, `${row.kind} · ${row.cell}`, big(await frame(row.sprite), 2));
}
if (want === "pixellab") {
  const partsTo = section("PixelLab parts · 16 px adapted layers (new names await the v5.1 registry)", "grid sand");
  for (const row of pixellab.parts.filter((p) => p.cell !== "generate")) figure(partsTo, `${row.part} · ${row.active ? "active" : "v5_pending"}`, big(await frame(`part.pixellab.${row.part}.16`), 2));
  const to = section("PixelLab fixtures · candidates for the lead", "grid sand");
  for (const row of pixellab.fixtures) figure(to, row.suggested_name, big(await frame(row.sprite), 2));
}
'''
    if '// Approved PixelLab import:' in preview:
        start=preview.index('// Approved PixelLab import:'); end=preview.index('const types = Object.keys(sprites)',start)
        preview=preview[:start]+block+'\n'+preview[end:]
    else:preview=preview.replace('const types = Object.keys(sprites)',block+'\nconst types = Object.keys(sprites)')
    (dest/'preview.html').write_text(preview)
    print(f"Imported {sum(r['cell']!='generate' for r in approved['kinds'])} kind heroes, {len(part_names)} part cells and {len(info['fixtures'])} fixture candidates from {len(names)-1} source sheets.")


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--incoming',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args();repo=args.repo
    import_art(repo,args.incoming or repo/'assets-incoming',args.output or repo,read(Path(__file__).with_name('pixellab-approved.json')))
