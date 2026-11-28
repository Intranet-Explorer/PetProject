"""The hub's own furniture (SPEC-v3.5.1 §3, §5). Needs Python 3.11+ and Pillow. From this folder:

  python3 hub.py        draws own/hub.png and lays this sheet's entries into ../../sprites.json as one block,
                        right after "fix.dial box.on"

`fix.terminal` is an old computer terminal on a small desk: a beige monitor with a dark glass, a keyboard before it.
The view writes on the glass itself (`glass` in its entry: what the pet typed, the text scrolling, green or amber).
`fix.radio set` is the pets' radio once it stands in the hub: a wooden console set with a dial window and a cloth
grille; `.on` has its dial lit. The lit sign and the statue are drawn by the view in code, not here."""
import json, os, re
import art
from build import ASSETS, Sheet, pic

TERMINAL = art.S("""
..############..
.#cccccccccccc#.
#aaaaaaaaaaaaaa#
#a############a#
#a#ssssssssss#a#
#a#ssssssssss#a#
#a#ssssssssss#a#
#a#ssssssssss#a#
#a#ssssssssss#a#
#a#ssssssssss#a#
#a#ssssssssss#a#
#a############a#
#aaaaaaaaaaaHaA#
#AAAAAAAAAAAAAA#
.##############.
#EEEE#TTTTTT#EE#
#E############E#
#E#aAaAaAaAaA#E#
#E#AaAaAaAaAa#E#
#E############E#
#eeeeeeeeeeeeee#
################
.#e#........#e#.
.#e#........#e#.
.#e#........#e#.
.###........###.
""")
GLASS = [3, 4, 10, 7]   # where the glass is in TERMINAL: [x, y, w, h]

RADIO = art.S("""
....########....
..##nnnnnnnn##..
.#nbbbbbbbbbbn#.
#nbBBBBBBBBBBbn#
#bB##########Bb#
#bB#AAAAAAAA#Bb#
#bB#ArAAmAAA#Bb#
#bB##########Bb#
#bBBBBBBBBBBBBb#
#bB##########Bb#
#bB#EkEkEkEk#Bb#
#bB#EkEkEkEk#Bb#
#bB#EkEkEkEk#Bb#
#bB#EkEkEkEk#Bb#
#bB#EkEkEkEk#Bb#
#bB#EkEkEkEk#Bb#
#bB##########Bb#
#bBB###BB###BBb#
#bBB#t#BB#t#BBb#
#bBB###BB###BBb#
#BBBBBBBBBBBBBB#
################
.#B#........#B#.
.###........###.
""")
DIAL = {"A": "Y", "m": "y"}   # on: the dial window lit, warm


def sheet():
    s = Sheet("hub.png", 4)
    s.add("fix.terminal", pic(TERMINAL), glass=GLASS)
    s.add("fix.radio set", pic(RADIO))
    s.add("fix.radio set.off", pic(RADIO))
    s.add("fix.radio set.on", pic(RADIO, DIAL))
    return s


if __name__ == "__main__":
    own = sheet().save()
    # sprites.json is kept by hand, one name to a line: this sheet's lines go in as one block right after "fix.dial box.on"
    path = os.path.join(ASSETS, "sprites.json")
    lines = [l for l in open(path).read().split("\n") if not re.match(r' "(%s)":' % "|".join(re.escape(n) for n in own), l)]
    at = next(i for i, l in enumerate(lines) if l.startswith(' "fix.dial box.on":'))
    lines[at + 1:at + 1] = [" %s: %s," % (json.dumps(n), json.dumps(e)) for n, e in own.items()]
    open(path, "w").write("\n".join(lines))
    print("drew %d pictures into own/hub.png" % len(own))
