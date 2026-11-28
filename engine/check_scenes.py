"""SPEC-v5.3 §6: scenes.py finds every scene from its facts alone, and names the missing rule of one that did not occur.

    uv run python -m engine.check_scenes
"""
from . import contracts as K
from .scenes import find, missing


def main():
    # a house of facts in which every scene occurs once
    h = {"tick": 0, "ticks_per_day": 100, "pets": {"a": {"name": "Ada", "drive": {"name": "to leave the house"}, "habits": [{"name": "keep company"}], "parents": ["m"]},
                                                     "b": {"name": "Bo", "habits": []}, "c": {"name": "Cy", "parents": ["m"]}}, "v5": {"projects": {}}}

    def at(t, what, **rec):
        h["tick"] = t
        K.event53(h, what, **rec)
    assert all(not v for v in find(h).values()) and set(missing(h)) == set(K.SCENES)
    at(1, "habit", pet="b", habit="collect"), at(1, "marked", pet="b", kind="pile"), at(2, "mess", pet="a", owner="b"), at(3, "moved", pet="a", owner="b")
    at(4, "resent", pet="b", against="a", cause="took_my_thing")
    at(5, "taken", pet="b", owner="a"), at(6, "marked", pet="b", kind="hoard"), at(7, "found", pet="c", owner="b"), at(8, "opinion", pet="c", about="b", cause="dishonest", delta=-0.2)
    at(10, "project", project="p1", kind="shelter", state="under way", owners=["a"]), at(20, "step", project="p1", pet="a", do="clear"), at(150, "step", project="p1", pet="a", do="cover")
    at(160, "project", project="p1", kind="shelter", state="done", owners=["a"]), at(170, "slept_out", pet="a", site="s1"), at(180, "came_in", pet="a", why="food")
    at(200, "praise", pet="c", to="a", pride=0.1), at(210, "resent", pet="b", against="a", cause="envy")
    at(220, "project", project="p2", kind="bridge", state="done", owners=["a", "b"]), at(230, "bond", a="b", b="a", level="close")
    at(240, "project", project="p3", kind="hearth", state="orphaned", owners=["m"]), at(250, "taken_up", project="p3", pet="a", was="c", kind="hearth")
    at(260, "round", a="a", b="b", n=2), at(261, "round", a="a", b="b", n=3), at(262, "thread", a="a", b="b", subject="the box", picked=False)
    at(300, "thread", a="b", b="a", subject="the box", picked=True)
    got = find(h)
    assert all(got[s] for s in K.SCENES), {s: v for s, v in got.items() if not v}
    assert missing(h) == {}
    h2 = {"tick": 0, "pets": {}, "v5": {}}
    K.event53(h2, "praise", pet="a", to="b", pride=0.2)
    assert missing(h2)["praise"] == "never: envy resented" and missing(h2)["pile"] == "never: a collect habit's go"
    print("scenes: every scene found from its facts; a missing one names its missing rule")


if __name__ == "__main__":
    main()
