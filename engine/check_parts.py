"""The parts library checked against itself (SPEC-v3.5 §1, §7.1): every part has its drawing fields and its pixels,
every spot named exists, every catalog kind's base and signature exist, every body slot's value has its pictures, and no
use an invention can have (SPEC-v3.5 §3.0, uses.json) is put together from more than three parts, on a spot that is not
there, or out of its square, and every part a use adds is given by some catalog kind.

    uv run python -m engine.check_parts

Reads view/assets only (no house, no minds, no Pillow). `problems()` is the composition rules as data says them."""
import itertools, json, struct, zlib
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / "view" / "assets"
SPOTS = {"tip", "top", "side", "base", "inside"}


def png(path):
    """An 8-bit RGBA picture as (width, height, rows of (r, g, b, a))."""
    raw = path.read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n", "%s is not a PNG" % path
    at, chunks = 8, {}
    while at < len(raw):
        n, kind = struct.unpack(">I4s", raw[at:at + 8])
        chunks[kind] = chunks.get(kind, b"") + raw[at + 8:at + 8 + n]
        at += 12 + n
    w, h, depth, colour, _, _, lace = struct.unpack(">IIBBBBB", chunks[b"IHDR"])
    assert (depth, colour, lace) == (8, 6, 0), "%s is not plain 8-bit RGBA" % path
    data, rows, prev = zlib.decompress(chunks[b"IDAT"]), [], bytearray(w * 4)
    for y in range(h):
        f, line = data[y * (w * 4 + 1)], bytearray(data[y * (w * 4 + 1) + 1:(y + 1) * (w * 4 + 1)])
        for i in range(len(line)):
            a, b, c = (line[i - 4] if i >= 4 else 0), prev[i], (prev[i - 4] if i >= 4 else 0)
            p = a + b - c
            line[i] = (line[i] + (0, a, b, (a + b) // 2, a if abs(p - a) <= abs(p - b) and abs(p - a) <= abs(p - c) else b if abs(p - b) <= abs(p - c) else c)[f]) & 255
        rows.append([tuple(line[i:i + 4]) for i in range(0, w * 4, 4)])
        prev = line
    return w, h, rows


def problems(lib, parts):
    """What is wrong with a thing made of these parts ([{"part", "at"}], the base first), by the rules in parts.json:
    at most `max_parts`, one base that everything else sits on, each on a spot the base has and the part may go on,
    no spot used twice (unless what is there `carries` it: a flame in a fork), and none of `no_stack` twice. An empty
    list: it may be made."""
    T, R, out = lib["thing"], lib["rules"], []
    if not parts or any(p["part"] not in T for p in parts):
        return ["a part the library does not have"]
    if len(parts) > R["max_parts"]:
        out.append("more than %d parts" % R["max_parts"])
    base, rest = parts[0], parts[1:]
    if T[base["part"]]["role"] != "base" or base.get("at"):
        out.append("the first part is not a base standing on nothing")
    for p in rest:
        if T[p["part"]]["role"] == "base":
            out.append("a second base (%s)" % p["part"])
        elif p.get("at") not in T[base["part"]].get("spots", []):
            out.append("%s on %r, a spot the %s does not have" % (p["part"], p.get("at"), base["part"]))
        elif p["at"] not in T[p["part"]]["on"]:
            out.append("%s cannot go on a %s" % (p["part"], p["at"]))
    for i, p in enumerate(rest):
        if any(q.get("at") == p.get("at") and p.get("at") not in T[q["part"]].get("carries", []) for q in rest[:i]):
            out.append("two parts on one spot")
    out += ["two of %s" % n for n in R["no_stack"] if sum(p["part"] == n for p in parts) > 1]
    return out


def place(lib, base, names):
    """The parts of a thing on this base: each added part on the first spot of its `on` list that the base has free, or
    that a part already there carries. None if one of them has nowhere to go. (The preview page places them so too.)"""
    T, taken, parts = lib["thing"], {}, [{"part": base, "at": None}]
    for n in names:
        at = next((s for s in T[n]["on"] if s in T[base]["spots"] and (s not in taken or s in T[taken[s]].get("carries", []))), None)
        if at is None:
            return None
        taken[at] = n
        parts.append({"part": n, "at": at})
    return parts


def templates(uses):
    """Every thing a use allows: (use, base, the parts added in order: the `may` part first, if it has it)."""
    for name, u in uses.items():
        for base in u["base"]:
            for add in itertools.product(*u["add"]):
                for may in [None] + list(u.get("may", [])):
                    yield name, base, ([may] if may else []) + list(add)


def main():
    lib, bodies, kinds, uses = (json.loads((ASSETS / f).read_text()) for f in ("parts.json", "bodies.json", "kinds.json", "uses.json"))
    uses = uses["uses"]
    T, R, pal = lib["thing"], lib["rules"], lib["palette"]
    known = {tuple(bytes.fromhex(h)) for v in pal.values() for h in ([v] if isinstance(v, str) else v)}
    sheets = {}
    sheet = lambda f: sheets.setdefault(f, png(ASSETS / f))

    def pixels(file, rect, what):
        """The drawn pixels of a rectangle of a sheet as {(x, y): colour}: there are some, and each is a colour of the palette."""
        w, h, rows = sheet(file)
        x0, y0, rw, rh = rect
        assert 0 <= x0 and 0 <= y0 and x0 + rw <= w and y0 + rh <= h and rw > 0 and rh > 0, "%s: its rectangle %s reaches outside %s" % (what, rect, file)
        px = {(x, y): rows[y0 + y][x0 + x][:3] for y in range(rh) for x in range(rw) if rows[y0 + y][x0 + x][3]}
        assert px, "%s: nothing is drawn in %s %s" % (what, file, rect)
        assert set(px.values()) <= known, "%s: a colour that is not in the palette" % what
        return px

    # ---- thing parts: the names the spec asks for, each drawn at every size, with its spots or its pin ----
    for name in ("stick", "bowl", "box", "disc", "ring", "frame", "cushion", "block", "bundle", "flame", "blade", "tines", "bell dome", "lid", "spout", "strings", "wheel", "hook",
                 "flower", "gem", "sail", "cord", "cloth", "band", "studs", "spade", "chimes", "pad", "seeds"):
        assert name in T, "the library has no %s" % name
    assert 40 <= len(T) + sum(len(s["values"]) for s in lib["body"]["slots"].values()) + len(lib["body"]["plans"]) <= 60, "about 40 to 60 parts"
    sizes, drawn = sorted(set(R["px"].values())), {}
    for name, p in T.items():
        assert p["role"] in ("base", "top", "wrap") and p.get("layer") in ("behind", "body", "front"), name
        assert set(p["spots"] if p["role"] == "base" else p["on"]) <= SPOTS and (p.get("spots") or p.get("on")), "%s names a spot there is no such thing as" % name
        for S in sizes:
            x = p.get("px", {}).get(str(S))
            assert x and x["rect"][2:] == [S, S], "%s is not drawn at %d pixels" % (name, S)
            px = pixels(x["file"], x["rect"], "%s at %d" % (name, S))
            inside = lambda q: len(q) == 2 and 0 <= q[0] < S and 0 <= q[1] < S
            if p["role"] == "base":
                assert set(p["spots"]) | {"face", "base"} <= set(x["at"]) and all(inside(q) for q in x["at"].values()), "%s at %d: a spot of it has no place" % (name, S)
            else:
                assert inside(x["pin"]), "%s at %d has no pin" % (name, S)
                assert all(inside(x.get("at", {}).get(c, [])) for c in p.get("carries", [])), "%s at %d carries a spot it has no place for" % (name, S)
            drawn[name, S] = px
    bases = [n for n, p in T.items() if p["role"] == "base"]
    for name, p in T.items():
        if p["role"] != "base":
            assert any(s in T[b]["spots"] for b in bases for s in p["on"]), "nothing has a spot %s can go on" % name
            for spot, to in p.get("to", {}).items():
                assert all(to in T[b]["px"][str(S)]["at"] for b in bases if spot in T[b]["spots"] for S in sizes), "%s: `to` sends %s to %s, which a base lacks" % (name, spot, to)
    assert set(R.get("behind", [])) <= SPOTS and set(R["no_stack"]) <= set(T) and R["max_parts"] == 3

    # ---- the catalog: every kind has its base and the part it gives an invention ----
    for kind in kinds:
        k = lib["kinds"].get(kind)
        assert k and T.get(k["base"], {}).get("role") == "base", "%s has no base part" % kind
        assert T.get(k["signature"], {}).get("role") in ("top", "wrap"), "%s has no signature part" % kind
    assert set(lib["kinds"]) <= set(kinds), "parts.json names a kind the catalog does not have"

    # ---- composition: the rules refuse what they should, and everything they allow fits its square ----
    P = lambda *names: [{"part": n.split("@")[0], "at": (n.split("@") + [None])[1]} for n in names]
    assert not problems(lib, P("stick", "flame@tip", "band@side")) and not problems(lib, P("bowl"))
    for bad in (P("stick", "flame@tip", "band@side", "cord@side"), P("stick", "lid@top"), P("stick", "spout@tip"), P("bowl", "flame@inside", "flame@top"), P("stick", "blade@tip", "blade@side"),
                P("flame"), P("box", "bowl@top"), P("bowl", "lid@top", "flower@top"), P("box", "nothing@top"), []):
        assert problems(lib, bad), "the rules let through %s" % bad
    assert not problems(lib, P("stick", "tines@tip", "flame@tip")) and problems(lib, P("stick", "flame@tip", "tines@tip")), "a flame stands in a fork, not a fork on a flame"

    # ---- the uses (§3.0): every part of every template exists, each goes together within its square at every size, and
    # every part a use adds is the signature of some kind, so the use can be reached from two things a pet can make ----
    given, count = {k["signature"] for k in lib["kinds"].values()}, 0
    for name, u in uses.items():
        assert u["base"] and u["add"] and all(u["add"]) and u.get("does"), "the use %s is not whole" % name
        assert all(T.get(b, {}).get("role") == "base" for b in u["base"]), "%s: a base that is not a base part" % name
        for n in [x for l in u["add"] for x in l] + list(u.get("may", [])):
            assert T.get(n, {}).get("role") in ("top", "wrap"), "%s: no part %r to add" % (name, n)
        for n in (x for l in u["add"] for x in l):
            assert n in given, "%s adds %s, which no catalog kind gives" % (name, n)
    # ... and a curio (two things that fit no use): any kind's base with any other kind's signature part on its first free spot
    shapes = [(name, base, names) for name, base, names in templates(uses)]
    shapes += sorted({("curio", a["base"], (b["signature"],)) for a in lib["kinds"].values() for b in lib["kinds"].values()})
    for name, base, names in shapes:
        parts = place(lib, base, list(names))
        assert parts and not problems(lib, parts), "%s: %s + %s cannot be put together (%s)" % (name, base, " + ".join(names), parts and problems(lib, parts))
        count += name != "curio"
        for S in sizes:
            B, held = T[base]["px"][str(S)], {}
            xs, ys = [x for x, _ in drawn[base, S]], [y for _, y in drawn[base, S]]
            for p in parts[1:]:
                t, x = T[p["part"]], T[p["part"]]["px"][str(S)]
                point = t.get("to", {}).get(p["at"], p["at"])
                spot, pin = held.get(point) or B["at"][point], x["pin"]   # (a missing spot is a KeyError: it must not happen)
                if point in t.get("carries", []):
                    held[point] = [spot[0] - pin[0] + x["at"][point][0], spot[1] - pin[1] + x["at"][point][1]]
                if t.get("clip"):
                    continue   # painted only on the base's own body
                xs += [a + spot[0] - pin[0] for a, _ in drawn[p["part"], S]]
                ys += [b + spot[1] - pin[1] for _, b in drawn[p["part"], S]]
            over = max(max(xs) - min(xs) + 1, max(ys) - min(ys) + 1) - S
            assert over <= 0, "%s: %s at %d pixels is %d too big for its square" % (name, " + ".join("%s%s" % (p["part"], "@" + p["at"] if p["at"] else "") for p in parts), S, over)

    # ---- body parts: every value of every slot has its pictures, every plan its proportions ----
    body = lib["body"]
    assert set(bodies["plans"]) <= set(body["plans"]) and all(0 < p["w"] <= 2 and 0 < p["h"] <= 2 for p in body["plans"].values()), "a body plan has no proportions"
    assert body["plans"]["blob"] == {"w": 1, "h": 1}, "the first plan is today's body"
    assert set(bodies["slots"]["shade"]) <= set(body["shade"]) and body["shade"][bodies["slots"]["shade"][0]] == 0, "a coat's shade has no tone"
    views, n = ["%s.%s" % (v, s) for v in ("front", "side", "back") for s in "sl"], 0
    faces = ["%s.%s.%s" % (e, c, s) for e in ("flat", "smile", "frown", "open", "o") for c in (1, 2, "side") for s in "sl"]
    for slot, values in bodies["slots"].items():
        if slot in ("fur", "shade"):   # a ragged edge and a darker coat: drawn by rule, not from a picture
            continue
        s = body["slots"].get(slot)
        assert s and s["layer"] in ("behind", "front", "on"), "the body slot %s is not drawn" % slot
        for v in values[0 if slot in ("feet", "mouth") else 1:]:   # the first value of the others is having none
            frames = s["values"].get(v, {}).get("frames", {})
            assert set(faces if slot == "mouth" else views) <= set(frames), "%s %s lacks a picture" % (slot, v)
            for name, f in frames.items():
                pixels(body["file"], f["rect"], "%s %s %s" % (slot, v, name))
                assert 0 <= f["pin"][0] < f["rect"][2] and 0 <= f["pin"][1] < f["rect"][3], "%s %s %s: its pin is outside it" % (slot, v, name)
                n += 1
    print("parts: %d thing parts at %s px, %d body pictures, %d kinds, %d uses in %d shapes and %d curio shapes, all within their squares" % (len(T), "/".join(map(str, sizes)), n, len(kinds), len(uses), count, len(shapes) - count))
    print("parts check passed")


if __name__ == "__main__":
    main()
