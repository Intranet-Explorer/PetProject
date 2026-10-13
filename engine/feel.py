"""Feel, don't count (SPEC-v3 §3). The numbers stay in the engine and the Lab; a pet is told how it feels,
what changed in words, and what it notices. This module is the only place that turns one into the other,
and it also reads a pet's words back into numbers so the engine can score what it expected."""
import re

from .world import NEEDS, days as world_days, dist

# Five felt states per need, best to worst, with the level each begins at. The words for one need are meant to
# be no louder than another's (v2's "restless" drowned out comfort): each list goes from good, to fine, to a
# mild lack, to a plain lack, to a strong one.
WORDS = {
    "energy": ["full of energy", "awake", "a bit tired", "tired", "exhausted"],
    "comfort": ["at ease", "fine", "uneasy", "uncomfortable", "miserable"],
    "curiosity": ["fascinated", "interested", "a bit bored", "bored", "restless for something new"],
    "company": ["close to someone", "not lonely", "a bit lonely", "lonely", "aching for company"],
}
GENE = {"comfort": "sensitive", "curiosity": "curious", "company": "sociable"}   # the gene that moves a need's thresholds
SEEMS = {   # how a pet looks to another, from its worst need (§7.1)
    "energy": ["lively", "awake", "a little tired", "tired", "worn out"],
    "comfort": ["content", "settled", "a little uneasy", "uncomfortable", "miserable"],
    "curiosity": ["absorbed", "interested", "a little bored", "bored", "restless"],
    "company": ["happy to have company", "content", "a little lonely", "lonely", "very lonely"],
}
MORE = {"energy": ("more rested", "more tired"), "comfort": ("more at ease", "less at ease"),
        "curiosity": ("more interested", "more bored"), "company": ("less alone", "more alone")}
SIZES = [(8, "a lot"), (3, "clearly"), (0.5, "a little")]


STEPS, SHIFT, TREND = [80, 60, 40, 20], 24, 0.8   # set from config.toml [feel] when the config is loaded (world.derive)
SEASONS = {}   # what each season asks, in a few words (SPEC-v3.5 §5): set from seasons.toml when the config is loaded (season.load)


def level(pet, need):
    """0 (best) to 4 (worst). A sensitive pet feels uncomfortable sooner, a curious one bored sooner,
    a sociable one lonely sooner: up to 12 points earlier, never said to it in so many words (§8.1)."""
    shift = (pet["temper"].get(GENE.get(need, ""), 0.5) - 0.5) * SHIFT
    return sum(pet["needs"][need] < s + shift for s in STEPS)


def feelings(pet):
    """Every need as a feeling, every time (§3.1), the worst first, with which way it is going when it is going
    fast. Whatever is at its worst is hard to think past, whichever need it is: no need is louder than another,
    but the bottom of any of them is loud."""
    out = []
    for n in sorted(NEEDS, key=lambda n: -level(pet, n)):
        rate, lvl = pet["trend"].get(n, 0), level(pet, n)
        out.append(WORDS[n][lvl] + (" (it is hard to think of anything else)" if lvl == 4 else "")
                   + (" and getting worse" if rate <= -TREND and lvl < 4 else " and getting better" if rate >= TREND else ""))
    return "; ".join(out)


def seems(pet):
    """How it looks from outside: its worst need, or content."""
    worst = max(NEEDS, key=lambda n: level(pet, n))
    return SEEMS[worst][level(pet, worst)]


def changed(deltas):
    """A change in the needs, as a creature would feel it: by size in words, never a number (§3.2)."""
    parts = []
    for n in NEEDS:
        d = deltas.get(n, 0)
        size = next((word for least, word in SIZES if abs(d) >= least), None)
        if size:
            parts.append("%s %s" % (size, MORE[n][d < 0]))
    return ", ".join(parts)


def result(text, own, meanwhile):
    """A step's result: what happened, how it left the pet, and apart from that what the time itself did."""
    # a need the step itself moved is not reported twice: "a lot more rested ... not from that, more tired" reads as nonsense
    felt, drift = changed(own), changed({n: d for n, d in meanwhile.items() if abs(own.get(n, 0)) < 0.5})
    # The separation has to name where the other change came from. "apart from that, while it lasted you grew a little
    # less at ease" was read as the price of the deed (third run: "Leaning toward Calm Seed costs ease", from a step
    # that does nothing to ease). Replaying the two nights on which a pet first wrote "cost" into a belief: 6 of 24
    # with the old words, 1 of 24 with these (DECISIONS, part 12).
    return text + ("; you feel " + felt if felt else "") + ("; not from that but from the hour and the place, you grew " + drift if drift else "")


def near_word(a, b):
    d = dist(a, b)
    return "beside you" if d <= 1 else "close by" if d <= 4 else "across the room"


def when(house):
    """The time, the season and the sky, as they would be noticed."""
    c, sky = house["clock"], house["weather"]
    part = "morning" if c["morning"] else "day" if c["phase"] == "day" else "dusk" if c["phase"] == "dusk" else "night"
    weather = {"clear": "the sky is clear", "cloudy": "the sky is grey", "rain": "it is raining", "storm": "there is a storm",
               "snow": "snow is falling", "heat": "the air is hot and still"}[sky]
    needs = SEASONS.get(c["season"])
    return "%s, in %s%s; %s" % (part, c["season"], " (%s)" % needs if needs else "", weather)


def ago(house, cfg, tick):
    days = world_days(cfg, tick, house["tick"])
    return "today" if days < 0.75 else "yesterday" if days < 1.75 else "%d days ago" % round(days)


# ---- reading a pet's words back (§3.2: `expect` is still scored against the real change) ----

# Words that name a need. Each has a pole: +1 if more of the word means the need is better met.
NAMES = {
    "energy": [(r"energy|rested|awake|lively|refreshed", 1), (r"tired|exhaust|sleepy|weary|worn|drained|fatigue", -1)],
    "comfort": [(r"comfort(?!able)|comfortable|at ease|ease|calm|cozy|cosy|settled|safe|warm|sooth|peace|relax|content|better", 1),
                (r"uneasy|uncomfortable|miserable|unease|harsh|cold|hurt|discomfort|worse|unsettled", -1)],
    "curiosity": [(r"curio|interest|fascinat|absorbed|engaged|entertain|delight|new", 1), (r"bored|boredom|restless|dull", -1)],
    "company": [(r"company|companion|close to|together|loved|befriend|less alone|not alone|connect", 1), (r"lonely|loneli|alone|aching", -1)],
}
UP = re.compile(r"\b(more|ris\w*|rais\w*|increas\w*|grow\w*|higher|gain\w*|restor\w*|improv\w*|recover\w*|return\w*|better|up|will feel|feel|become|becoming|get|getting)\b")
DOWN = re.compile(r"\b(less|no longer|not|stop\w*|fad\w*|eas\w*|drop\w*|fall\w*|lower\w*|decreas\w*|reduc\w*|los\w*|drain\w*|declin\w*|down|away|gone|lift\w*|pass\w*|relie\w*)\b")
SAME = re.compile(r"\b(same|unchanged|no change|stay\w*|still|steady|nothing)\b")
STATE = {"on": r"\bon\b|lit|glow", "off": r"\boff\b|dark|out", "playing": r"play|music|sound", "silent": r"silen|quiet|stop",
         "open": r"\bopen", "closed": r"clos|shut", "full": r"full|fill", "empty": r"empty", "ripe": r"ripe|grown", "half": r"half"}


def expected(text):
    """What a prediction says will happen to which need: (need, +1 | -1 | 0) or (None, None).
    "less tired" and "more rested" are both energy going up; "more bored" is curiosity going down."""
    s = text.lower()
    best = None
    for need, kinds in NAMES.items():
        for pattern, pole in kinds:
            m = re.search(r"\b(?:%s)\w*" % pattern, s)
            if m and (best is None or m.start() < best[0]):
                best = (m.start(), need, pole, m.end())
    if not best:
        return None, None
    at, need, pole, end = best
    before = s[max(0, at - 28):at]
    if SAME.search(before) or SAME.search(s[end:end + 24]):
        return need, 0
    down = DOWN.search(before)                       # "less", "no longer", "stops" just before the word flips it
    after = s[end:end + 30]
    if not down and re.search(r"\b(fad|eas|lift|pass|drop|fall|go(es)? (away|down)|decreas|lower|drain|wear)", after):
        down = True                                  # "the tiredness fades", "comfort drops"
    return need, pole * (-1 if down else 1)


def score(text, deltas, house, pet):
    """Score what it expected against what really happened: (correct | wrong | unscorable, the need it named)."""
    if not isinstance(text, str) or not text.strip():
        return "unscorable", None
    need, way = expected(text)
    if need:
        actual = (deltas.get(need, 0) >= 0.5) - (deltas.get(need, 0) <= -0.5)
        pinned = (way > 0 and pet["needs"][need] >= 99.5) or (way < 0 and pet["needs"][need] <= 0.5)
        if pinned and actual == 0:   # it expected more of what was already full: nothing could have shown it right
            return "unscorable", need
        return ("correct" if way == actual else "wrong"), need
    s, room = text.lower(), house["rooms"][pet["room"]]
    for name, o in room["objects"].items():           # a visible change: "the lamp is off", "the music box is playing"
        if "state" in o and name in s:
            for state, pattern in STATE.items():
                if re.search(pattern, s) and state in (o["state"], *o.get("fix", {}).get("states", []), "on", "off"):
                    return ("correct" if o["state"] == state else "wrong"), None
    return "unscorable", None


# ---- the meter-talk check (§3.4) ----

METER = re.compile(r"[+-]\s?\d|\d\s?%|\befficien|\boptimal|\boptimi[sz]|\bmaximi[sz]|\bcosts?\b|\brefund|\bactions?\b|bad target"
                   r"|\bt\d{2,}\b|\bticks?\b|\(\d+,\s?\d+\)|\bstat(s|us)?\b|\bmetric|\d\s?points?\b|\bcooldown|\bspike\b"
                   r"|\b(below|under|above|over|at|to) (ten|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|a hundred)\b", re.I)
# "points" counts only after a number ("6 points"). On its own it flagged the first showcase family's "the pulse
# points south" and "bright pulse point" (72 of 92 flags after the first day) and no meter-talk at all; v2.5's figure moves from 43.3% to 43.0% without it (DECISIONS, part 11).


def meter_talk(text):
    """Does this thought or belief talk mechanics: signed numbers, costs, refunds, actions, ticks, coordinates?"""
    return bool(METER.search(text or ""))
