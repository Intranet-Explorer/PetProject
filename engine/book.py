"""The book (SPEC-v3.1 §6): an offline copy of Simple English Wikipedia that a pet can ask a question. The file
is read on this Mac and nowhere else: nothing here opens a socket, and a question never leaves the house."""
import html
import re
from pathlib import Path

from . import firsts, hub
from .world import ROOT, arrived

STOP = set("a an the is are was were be been do does did what why how who where when which of in on to for and or it its this "
           "that there here can could would should will i me my you your we they them his her about from with into make made "
           "happen happens mean means come comes get gets go goes tell say thing things some any much many so not no".split())
_archive = {}


def path(cfg):
    return ROOT / cfg["book"]["zim"]


def available(cfg):
    """Is the encyclopedia installed? Until it is, the book is too faded to read and its arrival is held back."""
    try:
        import libzim   # noqa: F401
    except ImportError:
        return False
    return path(cfg).exists()


def archive(cfg):
    from libzim.reader import Archive
    p = str(path(cfg))
    if p not in _archive:
        _archive[p] = Archive(p)
    return _archive[p]


def plain(text, cfg):
    """Plain words only: no markup, no links, no footnote marks, nothing on the owner's blocklist (as for the radio)."""
    from . import radio
    return radio.clean(text, cfg, limit=10**6)


def passage(page, cfg, links=None):
    """About the first 400 characters of an article's own prose, ending on a whole sentence. `links`, a list: the
    titles the paragraphs read link to are added to it (SPEC-v5.1 §6.2)."""
    from .life import last_sentence
    page = re.sub(r"(?is)<(table|style|script|sup|figure|math)\b.*?</\1>", " ", page)
    out = ""
    for para in re.findall(r"(?is)<p\b[^>]*>(.*?)</p>", page):
        text = plain(html.unescape(re.sub(r"(?s)<[^>]+>", "", para)), cfg)
        if text and len(text) > 30:
            out = (out + " " + text).strip()
            if links is not None:
                links += [html.unescape(t) for t in LINK.findall(para) if ":" not in t]
        if len(out) >= cfg["book"]["chars"]:
            break
    return last_sentence(out, cfg["book"]["chars"] + 60) if out else None


def words(question):
    return [w for w in re.findall(r"[a-z][a-z'-]+", question.lower()) if w not in STOP and len(w) > 2]


NATURAL = ["zoology", "animal", "plant", "botany", "biology", "material", "geology", "rock", "mineral", "weather", "food", "tool",
           "insect", "bird", "fish", "fungus", "anatomy", "physics", "chemistry"]   # (in a title's brackets: the everyday or natural sense, best first)
ODD = re.compile(r"\b(company|corporation|plc|brand|band|album|song|single|film|movie|television|tv series|video game|politician|footballer|"
                 r"singer|actor|actress|rapper|businessman|businesswoman|wrestler|novel|magazine|newspaper)\b", re.I)


def main_words(question):
    """The words of what is asked about: question words and the rest of the asking stripped, and only the first
    run of words before "of", "for", "to" and the like ("how to make supple reed" -> supple, reed)."""
    for part in re.split(r"\b(?:of|for|in|on|with|from|into|to|about|by|at)\b", question.lower()):
        if words(part):
            return words(part)
    return words(question)


def read(a, path, cfg):
    """(title, passage) of one article, or None: not a page of words, a list of meanings, or about a company, a
    band, a film or a person of that kind (by its first sentence). Its links are kept in LINKS[title] (SPEC-v5.1)."""
    links = []
    try:
        entry = a.get_entry_by_path(path)
        item = entry.get_item()
        if not item.mimetype.startswith("text/html"):
            return None
        text = passage(bytes(item.content).decode("utf-8", "replace"), cfg, links)
    except Exception:
        return None
    if not text or re.search(r"(may|can|could) (refer to|mean)", text) or ODD.search(text.split(". ")[0]):
        return None
    LINKS[entry.title] = [t for t in dict.fromkeys(links) if t.lower() != entry.title.lower()][:5]
    while len(LINKS) > 200:
        LINKS.pop(next(iter(LINKS)))
    return entry.title, text


def lookup(cfg, question):
    """The best-matching article for a question: (its title, a passage), or None (14 October 2026). The thing asked
    about is tried as a title (the whole of it, then its last word, the noun: "supple reed" -> "reed"), and where a
    title is a list of meanings, its everyday or natural sense ("Shell (zoology)", not Shell plc); the whole text of
    the book only after that, and never a company, a band or a film."""
    from libzim.search import Query, Searcher
    from libzim.suggestion import SuggestionSearcher
    a, asked = archive(cfg), main_words(question)
    if not asked:
        return None
    head = asked[-1]
    for q in dict.fromkeys([" ".join(asked), head] + ([head[:-1]] if head.endswith("s") else []) + asked):
        hits = list(SuggestionSearcher(a).suggest(q).getResults(0, 40))
        say = lambda p: p.replace("_", " ").lower()
        exact = [p for p in hits if say(p) in (q, q + "s")]
        kinds = {p: say(p)[len(q) + 2:-1] for p in hits if say(p).startswith(q + " (") and say(p).endswith(")")}
        natural = sorted((p for p, k in kinds.items() if k in NATURAL), key=lambda p: NATURAL.index(kinds[p]))
        for p in exact + natural:
            got = read(a, p, cfg)
            if got:
                return got
    for p in Searcher(a).search(Query().set_query(" ".join(asked))).getResults(0, 10):
        got = read(a, p, cfg)
        if got:
            return got
    return None


def page(cfg, question):
    """One of the book's own pages (crafting.toml [[entry]]), if the question has one of its words."""
    asked = set(words(question))
    return next((e for e in cfg["craft"].get("entry", []) if asked & set(e["words"])), None)


def entry(cfg, question):
    """... as (title, text)."""
    e = page(cfg, question)
    return (e["title"], e["text"]) if e else None


def check_ask(a, house, cfg, pet, filled):
    room = house["rooms"][pet["room"]]
    if not any(o.get("fix", {}).get("book") for o in room["objects"].values()):
        return "there is no book here"
    if not filled(a.get("question")):
        return "nothing to ask"
    if hub.book_at(house, cfg, room, pet)[0] is None:
        return "someone else is at every screen here; wait for one"
    if not arrived(house, "book") and not any(o.get("fix", {}).get("book") and not o["fix"].get("terminal") for o in room["objects"].values()):
        return "the screen is dark: nothing comes up on it yet"   # SPEC-v3.5.1 §3: the screens read the book's encyclopedia, which has not come yet
    if house["tick"] - pet.get("asked_at", -10**9) < hub.wait_hours(cfg, room) * cfg["ticks_per_hour"]:   # SPEC-v3.5.1 §3: less long at a screen
        return "your eyes are still tired from the small writing; later"
    return None


# ---- SPEC-v5.1 §6 (helper B): the book is the library. Switch: [book2] on (contracts.on51) ----

LINK = re.compile(r'<a\b[^>]*\brel="mw:WikiLink"[^>]*\btitle="([^"]+)"')
LINKS = {}   # title -> up to five titles its passage links to (filled by `read`)
ASK = {"material": "what is {w}", "death": "what is {w}", "happening": "what is {w}", "first_seen": "what is a {w}", "heard": "what is {w}", "visitor": "{w}"}   # §6.3 the engine's question, by source
ARTICLED = ("material", "heard")   # (their word gets world.a: "a reed", "clay")
DIED_OF = {"old age": "old age", "sickness": "a sickness", "injury": "an injury", "bad food": "bad food", "killing": "killing", "manslaughter": "a fall",
           "exposure": "the cold", "starvation": "hunger", "neglect": "wasting away"}
HAPPENED = {"storm": "a storm", "buried": "a buried thing", "stranger_egg": "an egg", "bad_food": "bad food", "missing": "getting lost", "cold_snap": "frost",
            "heat_wave": "a heat wave", "leak": "a leak", "power_cut": "electricity", "letter": "a letter", "dream": "a dream", "train": "a train",
            "creature": "a wild animal", "visitor_gone": "a visitor"}
_known_of = {}


def on(cfg):
    from . import contracts
    return contracts.on51(cfg, "book2")


def known_of(cfg):
    """API51 §6.4: {title, lower-case: [catalog kinds it teaches exist]}, from book/known_of.toml (kind -> titles)."""
    import tomllib
    p = ROOT / (cfg.get("book2") or {}).get("known_of", "book/known_of.toml")
    if p not in _known_of:
        out = {}
        for kind, titles in (tomllib.loads(p.read_text()) if p.exists() else {}).items():
            for t in titles:
                out.setdefault(t.lower(), []).append(kind)
        _known_of[p] = out
    return _known_of[p]


def tally(house, what, n=1):
    """SPEC-v5.1 §6.3 questions from life, for the rehearsal and the Lab: raised, read, found nothing, aged out."""
    t = house.setdefault("v5", {}).setdefault("questions51", {})
    t[what] = t.get(what, 0) + n


def retry(cfg, q):
    """the owner (21 October 2026): a question that found nothing is tried once more by title: its main words alone, then
    a known_of title with one of them in it. (title, passage) or None."""
    if not available(cfg):
        return None
    main = main_words(q)
    got = lookup(cfg, " ".join(main)) if main else None
    for t in ([] if got else [t for t in known_of(cfg) if set(words(t)) & set(main)]):
        got = lookup(cfg, t)
        if got:
            break
    return got


def wonder(house, cfg, pet, source, word):
    """§6.3 a question from life, kept for wants.candidates (a want of kind "word" with the engine's question):
    pet["questions"], the last four. Returns the question, or None."""
    from .world import a
    if not on(cfg) or not word or pet["stage"] in ("egg", "dead", "hatchling"):
        return None
    w = re.sub(r"\s+", " ", str(word)).strip().lower().rstrip("?")[:cfg["book"]["max_question"]]
    q = ASK[source].format(w=a(w) if source in ARTICLED and w else w)[:cfg["book"]["max_question"]]
    qs = pet.setdefault("questions", [])
    if not w or q in pet.get("asked", []) or any(x["question"] == q for x in qs):
        return None
    qs.append({"source": source, "word": w, "question": q, "tick": house["tick"]})
    tally(house, "raised")
    del qs[:-4]
    return q


def died(house, cfg, dead):
    """(Engine.kill) Those who knew it wonder what it died of."""
    from . import contracts as K
    from .world import family, relation
    cause = K.OLD_CAUSE.get(dead.get("cause"), dead.get("cause"))
    for p in house["pets"].values():
        if p is not dead and p["stage"] not in ("egg", "dead") and (family(p) == family(dead) or relation(house, p, dead)):
            wonder(house, cfg, p, "death", DIED_OF.get(cause, cause or "dying"))


def heard(house, cfg, pet, text):
    """(memories.from_talk) A thing named in a talk's `knows` line that it has no word for: a question."""
    from .wants import noun
    if not on(cfg):
        return None
    words = pet.setdefault("words", [])
    new = next((n for n in (noun(cfg, w) for w in re.findall(r"[a-z]{3,}", str(text).lower())) if n and n not in words), None)
    if new:
        words.append(new)
        return wonder(house, cfg, pet, "heard", new)
    return None


def bookish(pet):
    return (pet.get("drive") or {}).get("name") == "to know everything in the book"


def onward(cfg, pet):
    """§6.2 does it read on from a link: curious enough, or its drive is the book."""
    from .character import trait
    return bookish(pet) or ("temper" in pet and trait(pet, "curious") >= cfg["book2"]["curious"])


def next_read(house, cfg, pet):
    """(wants.lean) What it would read next of its own accord: (question, the step's key) or (None, None). A learn
    aim's own question first (the model's: the aim's "question", or its words after "find out"); else, for one who reads
    on, a link of the passage it read last today, while the chain is short of [book2] chain_most."""
    from . import contracts as K
    from .planner import current
    if not on(cfg):
        return None, None
    asked, aim = pet.get("asked", []), current(pet)
    if aim and aim["kind"] == "learn":
        q = aim.get("question") or (re.sub(r"\s+in the book$", "", aim["text"][9:]) if aim["text"].startswith("find out ") else None)
        if q and q.lower() not in asked:
            return q[:cfg["book"]["max_question"]], "learn:" + q
    last = (pet.get("read") or [None])[0]
    if not last or not onward(cfg, pet) or house["tick"] - last.get("tick", 0) >= cfg["ticks_per_day"] or K.read(last)["chain"] + 1 >= cfg["book2"]["chain_most"]:
        return None, None
    nxt = next((t for t in last.get("links") or [] if t.lower() not in asked), None)
    return (nxt, "on:" + nxt) if nxt else (None, None)


def record(house, cfg, pet, q, title, text):
    """The read, contracts.read: where it came from (a link of the last passage is "on", a question from life its
    source, else "own"), its links and the kinds it teaches of."""
    from . import contracts as K
    last, ql = (pet.get("read") or [None])[0], q.lower()
    src, chain = "own", 0
    if last and ql in [t.lower() for t in last.get("links") or []]:
        src, chain = K.read(last)["source"], K.read(last)["chain"] + 1   # (a read on keeps its chain's source; it is counted as "on")
    else:
        x = next((x for x in pet.get("questions", []) if x["question"] == ql or x["word"] in ql), None)
        if x:
            src = x["source"]
            pet["questions"].remove(x)
    return K.read({"tick": house["tick"], "question": q, "title": title, "text": text, "links": LINKS.get(title, []), "chain": chain, "source": src,
                   "kinds": known_of(cfg).get(title.lower(), [])})


def took(house, cfg, pet, rec, at):
    """What a read leaves: counted by source, knowing-of the kinds it teaches, its memory, a chain of three a first,
    and the reading list on the screen it was read at (§6.5)."""
    from . import contracts as K, knowledge
    K.count(house, "read", "on" if rec["chain"] else rec["source"])
    for k in rec["kinds"]:
        knowledge.learn(house, cfg, pet, K.key_of(k), "read", of=True)
    remember(house, cfg, pet, rec)
    if rec["chain"] + 1 >= cfg["book2"]["chain_most"]:
        K.count(house, "chain", pet["id"])
        firsts.chain(house, cfg, pet)
    o = house["rooms"][pet["room"]]["objects"].get(at or "")
    if o and o.get("screen"):
        o["screen"]["list"] = [r["title"] for r in pet["read"][:5] if r.get("title")]


def sentence(text):
    """The passage's first sentence as what it read: "a millstone is a stone ...", a common noun's capital let down."""
    s = (re.split(r"(?<=[.!?])\s", text.strip(), maxsplit=1)[0] or text).strip()[:200]
    first = s.split(" ", 1)[0]
    if first and first[0].isupper() and (first.lower() in ("a", "an", "the", "some", "many", "most", "this", "these", "it", "they", "there")
                                         or re.search(r"\b%s\b" % re.escape(first.lower()), text[len(first):])):
        s = s[0].lower() + s[1:]
    return s if s.endswith((".", "!", "?")) else s + "."


def remember(house, cfg, pet, rec):
    """API51 §6.1: a read is a memory: "I read that a millstone grinds grain between two stones", weight 3, kind "read",
    its tags the title, the kinds it teaches of and the material words in it."""
    from . import grammar, memories
    low = rec["text"].lower()
    mats = [m for m in grammar.data()["material"] if re.search(r"\b%s\b" % re.escape(m), low)]
    return memories.remember(house, cfg, pet, "I read that " + sentence(rec["text"]), 3, "read", what=[rec["title"]] + list(rec["kinds"]) + mats)


def ask(house, cfg, pet, a, clean):
    """`ask_book`: the pet turns the pages looking for what it asked, and reads what it finds."""
    from .world import label, moment
    from . import craft, wants
    q = clean(a["question"], cfg["book"]["max_question"])
    pet["asked_at"] = house["tick"]
    pet["asked"] = (pet.get("asked", []) + [q.lower()])[-12:]   # SPEC-v3.4 §4.1: a word it wondered about has been asked after
    craft.practise(house, cfg, pet, "reading")
    found = entry(cfg, q) or (lookup(cfg, q) if available(cfg) else None)
    life = on(cfg) and any(x["question"] == q.lower() for x in pet.get("questions", []))
    if not found and life:
        found = retry(cfg, q)
    at = hub.book_at(house, cfg, house["rooms"][pet["room"]], pet)[0]   # SPEC-v3.5.3 §10: a screen is a screen, not the book
    book = "the screen" if house["rooms"][pet["room"]]["objects"].get(at or "", {}).get("fix", {}).get("terminal") else "the book"
    # a tool it wants (13 October 2026): it has been to the book about it; and a page that says what one is made of has told it
    own, asked = page(cfg, q) or {}, set(words(q))
    for tool, T in cfg["craft"]["tool"].items():
        if own.get("tool") == tool or (tool in pet.get("lacks", {}) and asked & (set(words(T["want"])) - {"something"} | {tool})):
            pet["asked_tool"] = list(dict.fromkeys(pet.get("asked_tool", []) + [tool]))
        if own.get("tool") == tool:
            pet["takes"] = list(dict.fromkeys(pet.get("takes", []) + [tool]))
    for w in pet.get("wants", []):
        if w["what"] in ("tool", "word"):
            w["touched"] = house["tick"]
    hub.show(house, cfg, pet, house["rooms"][pet["room"]], q, found)   # SPEC-v3.5.1 §3: up on the screen's glass
    house.setdefault("fresh_reads", []).append({"pet": pet["id"], "tick": house["tick"], "question": q,
                                                "title": found[0] if found else None, "text": found[1] if found else None})
    if life:
        tally(house, "read" if found else "found nothing")
    if not found:
        if on(cfg):
            pet["questions"] = [x for x in pet.get("questions", []) if x["question"] != q.lower() and x["word"] not in q.lower()]   # (asked: the want is met)
        moment(house, "read", "%s asked %s \"%s\" and found nothing" % (label(pet), book, q), pet["id"], pet["room"])
        return "you %s a long time and found nothing about that" % ("searched the screen" if book == "the screen" else "turned the pages"), {}, "ask book"
    title, text = found
    if on(cfg):   # SPEC-v5.1 §6 (helper B): a read with its links, where it came from, what it teaches of; a memory
        rec = record(house, cfg, pet, q, title, text)
        pet.setdefault("read", []).insert(0, rec)
        took(house, cfg, pet, rec, at)
    else:
        pet.setdefault("read", []).insert(0, {"tick": house["tick"], "question": q, "title": title, "text": text})
    del pet["read"][6:]
    firsts.read(house, cfg, pet, title)   # SPEC-v3.5.4 §6: a passage read for the first time
    house["read_glow"] = house["tick"]
    moment(house, "read", "%s asked %s \"%s\" and read about %s" % (label(pet), book, q, title), pet["id"], pet["room"])
    hint = wants.hinted(house, cfg, pet, title, text)   # what it read may point at something to try: a hint, never a recipe
    return 'you read %s, under "%s": "%s"%s' % ("on the screen" if book == "the screen" else "in the book", title, text, "; " + hint if hint else ""), dict(cfg["effects"]["read"]), "read " + title
