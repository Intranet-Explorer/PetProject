"""A pet's own memory (SPEC §8, SPEC-v3 §8.3): its append-only journal, its beliefs with where each came
from, and what it knows of itself. One folder per pet, under its lineage."""
import json
import re
from pathlib import Path


class Memory:
    def __init__(self, directory, cfg, db=None, pet_id=""):
        self.dir, self.db, self.pet_id, self.max = Path(directory), db, pet_id, cfg["beliefs"]["max_active"]
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "beliefs.json"
        self.beliefs = json.loads(self.path.read_text()) if self.path.exists() else []

    def update_self(self, **facts):
        path = self.dir / "self.json"
        me = json.loads(path.read_text()) if path.exists() else {}
        path.write_text(json.dumps({**me, **facts}, indent=1))

    def journal(self, rec):
        with (self.dir / "journal.jsonl").open("a") as f:
            f.write(json.dumps(rec) + "\n")

    def active(self):
        return [b for b in self.beliefs if b["status"] == "active"]

    def is_active(self, bid):
        return any(b["id"] == bid for b in self.active())

    def kept(self, since):
        """Beliefs still held that were first written at or before the given tick (SPEC-v2 §6, Adult)."""
        return [b for b in self.active() if b["created"] <= since]

    def to_review(self):
        """The one belief looked at again tonight (§3.3): the one longest unexamined."""
        held = self.active()
        return min(held, key=lambda b: (b.get("reviewed", b["created"]), b["created"])) if held else None

    def handle(self, statement):
        """What a belief is called: a word of its own that no other belief of this pet's has, never a number."""
        from .story import content
        used = {b["id"] for b in self.beliefs}
        words = [w for w in re.findall(r"[a-z]+", statement.lower()) if len(w) >= 4 and content(w)]
        for name in words + ["%s-%s" % (a, b) for a, b in zip(words, words[1:])] + ["%s-%s" % (w, x) for w in words[:3] for x in ("again", "still", "also", "more", "anew")]:
            if name not in used:
                return name
        return "belief-" + "".join(chr(97 + int(c)) for c in str(len(self.beliefs)))

    def write(self, statement, tick, source="lived"):
        if len(self.active()) >= self.max:
            return None
        b = {"id": self.handle(statement), "statement": statement, "source": source,
             "created": tick, "revised": tick, "status": "active"}
        self.beliefs.append(b)
        self._save(b, "write", tick)
        return b["id"]

    def revise(self, bid, statement, tick, reviewed=False):
        b = next(b for b in self.beliefs if b["id"] == bid)
        b["revised"] = tick
        if reviewed:
            b["reviewed"] = tick
        if statement is None:
            op = "keep"
        elif statement.lower() == "discard":
            b["status"], op = "discarded", "discard"   # stays in the file; history is never deleted
        else:
            b["statement"], op = statement, "revise"
        self._save(b, op, tick)

    def _save(self, b, op, tick):
        self.path.write_text(json.dumps(self.beliefs, indent=1))
        if self.db:
            from .log import put
            put(self.db, "beliefs", pet=self.pet_id, tick=tick, belief=b["id"], op=op, statement=b["statement"], source=b.get("source", "lived"))
