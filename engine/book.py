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
    """Plain words only: no markup, no links, no footnote marks, nothing on Tyler's blocklist (as for the radio)."""
    from . import radio
    return radio.clean(text, cfg, limit=10**6)


def passage(page, cfg):
    """About the first 400 characters of an article's own prose, ending on a whole sentence."""
    from .life import last_sentence
    page = re.sub(r"(?is)<(table|style|script|sup|figure|math)\b.*?</\1>", " ", page)
    out = ""
    for para in re.findall(r"(?is)<p\b[^>]*>(.*?)</p>", page):
        text = plain(html.unescape(re.sub(r"(?s)<[^>]+>", "", para)), cfg)
        if text and len(text) > 30:
            out = (out + " " + text).strip()
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
    band, a film or a person of that kind (by its first sentence)."""
    try:
        entry = a.get_entry_by_path(path)
        item = entry.get_item()
        if not item.mimetype.startswith("text/html"):
            return None
        text = passage(bytes(item.content).decode("utf-8", "replace"), cfg)
    except Exception:
        return None
    if not text or re.search(r"(may|can|could) (refer to|mean)", text) or ODD.search(text.split(". ")[0]):
        return None
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


def ask(house, cfg, pet, a, clean):
    """`ask_book`: the pet turns the pages looking for what it asked, and reads what it finds."""
    from .world import label, moment
    from . import craft, wants
    q = clean(a["question"], cfg["book"]["max_question"])
    pet["asked_at"] = house["tick"]
    pet["asked"] = (pet.get("asked", []) + [q.lower()])[-12:]   # SPEC-v3.4 §4.1: a word it wondered about has been asked after
    craft.practise(house, cfg, pet, "reading")
    found = entry(cfg, q) or (lookup(cfg, q) if available(cfg) else None)
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
    if not found:
        moment(house, "read", "%s asked %s \"%s\" and found nothing" % (label(pet), book, q), pet["id"], pet["room"])
        return "you %s a long time and found nothing about that" % ("searched the screen" if book == "the screen" else "turned the pages"), {}, "ask book"
    title, text = found
    pet.setdefault("read", []).insert(0, {"tick": house["tick"], "question": q, "title": title, "text": text})
    del pet["read"][6:]
    firsts.read(house, cfg, pet, title)   # SPEC-v3.5.4 §6: a passage read for the first time
    house["read_glow"] = house["tick"]
    moment(house, "read", "%s asked %s \"%s\" and read about %s" % (label(pet), book, q, title), pet["id"], pet["room"])
    hint = wants.hinted(house, cfg, pet, title, text)   # what it read may point at something to try: a hint, never a recipe
    return 'you read %s, under "%s": "%s"%s' % ("on the screen" if book == "the screen" else "in the book", title, text, "; " + hint if hint else ""), dict(cfg["effects"]["read"]), "read " + title
