"""The book (SPEC-v3.1 §6): an offline copy of Simple English Wikipedia that a pet can ask a question. The file
is read on this Mac and nowhere else: nothing here opens a socket, and a question never leaves the house."""
import html
import re
from pathlib import Path

from .world import ROOT

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


def lookup(cfg, question):
    """The best-matching article for a question: (its title, a passage), or None. Titles are tried first, the
    question's own words in order, then the whole text of the book."""
    from libzim.search import Query, Searcher
    from libzim.suggestion import SuggestionSearcher
    a, asked = archive(cfg), words(question)
    tries = [" ".join(asked)] + asked + [w[:-1] for w in asked if w.endswith("s")]
    paths = []
    for q in dict.fromkeys(t for t in tries if t):
        paths += [p for p in SuggestionSearcher(a).suggest(q).getResults(0, 1) if p.replace("_", " ").lower() in (q, q + "s", q.rstrip("s"))]
    if asked:
        paths += list(Searcher(a).search(Query().set_query(" ".join(asked))).getResults(0, 3))
    for p in dict.fromkeys(paths):
        try:
            entry = a.get_entry_by_path(p)
            item = entry.get_item()
            if not item.mimetype.startswith("text/html"):
                continue
            text = passage(bytes(item.content).decode("utf-8", "replace"), cfg)
        except Exception:
            continue
        if text:
            return entry.title, text
    return None


def entry(cfg, question):
    """One of the book's own pages (crafting.toml [[entry]]), if the question has one of its words: (title, text)."""
    asked = set(words(question))
    return next(((e["title"], e["text"]) for e in cfg["craft"].get("entry", []) if asked & set(e["words"])), None)


def check_ask(a, house, cfg, pet, filled):
    room = house["rooms"][pet["room"]]
    if not any(o.get("fix", {}).get("book") for o in room["objects"].values()):
        return "there is no book here"
    if not filled(a.get("question")):
        return "nothing to ask"
    if house["tick"] - pet.get("asked_at", -10**9) < cfg["book"]["per_hours"] * cfg["ticks_per_hour"]:
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
    house.setdefault("fresh_reads", []).append({"pet": pet["id"], "tick": house["tick"], "question": q,
                                                "title": found[0] if found else None, "text": found[1] if found else None})
    if not found:
        moment(house, "read", "%s asked the book \"%s\" and found nothing" % (label(pet), q), pet["id"], pet["room"])
        return "you turned the pages a long time and found nothing about that", {}, "ask book"
    title, text = found
    pet.setdefault("read", []).insert(0, {"tick": house["tick"], "question": q, "title": title, "text": text})
    del pet["read"][6:]
    house["read_glow"] = house["tick"]
    moment(house, "read", "%s asked the book \"%s\" and read about %s" % (label(pet), q, title), pet["id"], pet["room"])
    hint = wants.hinted(house, cfg, pet, title, text)   # what it read may point at something to try: a hint, never a recipe
    return 'you read in the book, under "%s": "%s"%s' % (title, text, "; " + hint if hint else ""), dict(cfg["effects"]["read"]), "read " + title
