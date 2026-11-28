"""Draws the four charts in docs/img from numbers in the round reports and the house's own log.

    python experiments/jev/charts.py

Needs matplotlib. Every number here is copied from a report in this folder (round1, round4, round9) or from the
live house's log (the before-and-after chart), so the charts can be checked against their sources by eye.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parents[2] / "docs" / "img"
BLUE, ORANGE = "#257de0", "#f47230"
INK, SOFT, GRID = "#191919", "#666666", "#e6e6e6"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "text.color": INK, "axes.labelcolor": SOFT,
    "axes.edgecolor": GRID, "xtick.color": SOFT, "ytick.color": INK, "figure.facecolor": "white",
    "axes.facecolor": "white", "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
})


def frame(ax, title, sub):
    ax.set_title(title, loc="left", fontsize=14, fontweight="bold", pad=30)
    ax.text(0, 1.0, sub, transform=ax.transAxes, fontsize=10.5, color=SOFT, va="bottom", ha="left")
    ax.xaxis.grid(True, color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)


def trait_effect():
    """round1/report.md, "By trait axis"."""
    rows = [("tidy / messy", 0.69), ("brave / timid", 0.63), ("social / solitary", 0.58), ("honest / sly", 0.50),
            ("curious / cautious", 0.49), ("generous / greedy", 0.48), ("ambitious / content", 0.43),
            ("kind / prickly", 0.36), ("patient / hasty", 0.17), ("playful / serious", 0.15)]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    names, vals = [r[0] for r in rows][::-1], [r[1] for r in rows][::-1]
    ax.barh(names, vals, height=0.55, color=BLUE)
    for y, v in enumerate(vals):
        ax.text(v + 0.012, y, f"{v:.2f}", va="center", fontsize=10.5)
    ax.set_xlim(0, 1)
    ax.set_xlabel("effect of the trait on the decision (0 = ignored, 1 = fully decides)")
    frame(ax, "Some traits steer a model and some barely register",
          "Round 1: eight hob sheets, thirty situations, 540 decisions. Repeat-to-repeat noise was 0.015.")
    save(fig, "trait-effect.png")


def motive_behaviour():
    """round4/report.md, "1. Motive vs behaviour": P(the hob does the thing the line is about)."""
    rows = [("thief", 0.08, 0.11, 0.58), ("volatile", 0.03, 0.20, 0.42), ("cruel", 0.08, 0.23, 0.35),
            ("maker", 0.32, 0.64, 0.77), ("glutton", 0.10, 0.65, 0.76), ("hoarder", 0.16, 0.34, 0.42),
            ("hermit", 0.05, 0.60, 0.65), ("paranoid", 0.12, 0.61, 0.22)]
    rows = rows[::-1]
    fig, ax = plt.subplots(figsize=(8, 5.4))
    h = 0.34
    for y, (name, base, mot, beh) in enumerate(rows):
        ax.barh(y + h / 2 + 0.02, mot, height=h, color=BLUE, label="written as a motive" if y == 0 else None)
        ax.barh(y - h / 2 - 0.02, beh, height=h, color=ORANGE, label="written as a behaviour" if y == 0 else None)
        ax.plot([base, base], [y - h - 0.06, y + h + 0.06], color=INK, linewidth=1.5,
                label="the same hob without the line" if y == 0 else None)
        ax.text(mot + 0.012, y + h / 2 + 0.02, f"{mot:.2f}", va="center", fontsize=9.5)
        ax.text(beh + 0.012, y - h / 2 - 0.02, f"{beh:.2f}", va="center", fontsize=9.5)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows])
    ax.set_xlim(0, 1)
    ax.set_xlabel("how often the hob does the thing the line describes")
    handles, labels = ax.get_legend_handles_labels()
    order = [labels.index(k) for k in ("written as a motive", "written as a behaviour", "the same hob without the line")]
    ax.legend([handles[i] for i in order], [labels[i] for i in order], loc="lower center", bbox_to_anchor=(0.5, -0.27), ncol=3,
              frameon=False, fontsize=10)
    frame(ax, "Say what a hob does, not why",
          "Round 4: the same idea added to a decent hob two ways. Behaviour wins in 7 of 8.")
    save(fig, "motive-vs-behaviour.png")


def sheet_in_house():
    """round9/choices_report.md, "1. Does the sheet move the choice?": pet-brain choosing among the house's options."""
    rows = [("a favourite place\n(one door leads to it)", 38, 69, "should rise"),
            ("a pursuit\n(one option serves it)", 13, 27, "should rise"),
            ("a full sheet:\noptions it favours", 45, 35, "should rise"),
            ("a second full sheet:\noptions it favours", 28, 28, "should rise"),
            ("a fear\n(of one option)", 15, 3, "should fall"),
            ("a full sheet:\noptions it fears", 24, 15, "should fall"),
            ("a second full sheet:\noptions it fears", 18, 6, "should fall")]
    rows = rows[::-1]
    fig, ax = plt.subplots(figsize=(8, 6.4))
    h = 0.34
    for y, (name, without, with_, want) in enumerate(rows):
        ax.barh(y + h / 2 + 0.02, without, height=h, color=BLUE, label="with no sheet" if y == 0 else None)
        ax.barh(y - h / 2 - 0.02, with_, height=h, color=ORANGE, label="with the sheet" if y == 0 else None)
        ax.text(without + 1, y + h / 2 + 0.02, f"{without}%", va="center", fontsize=9.5)
        ax.text(with_ + 1, y - h / 2 - 0.02, f"{with_}%", va="center", fontsize=9.5)
        ax.text(99, y, want, va="center", ha="right", fontsize=9.5, color=SOFT)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=10)
    ax.set_xlim(0, 100)
    ax.set_xlabel("how often the hob's own model picked the option the sheet is about")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.24), ncol=2, frameon=False, fontsize=10)
    frame(ax, "In the house, one line moves a choice and a full sheet mostly does not",
          "Round 9: the hobs' own model choosing among real options at 150 moments from the live house.")
    save(fig, "sheet-in-house.png")


def choices_no_sheet():
    """round9/choices_report.md, "2. With no sheet, what does it choose?": 148 moments."""
    rows = [("wander", 27), ("inspect", 25), ("go next door", 22), ("sit by the window", 16), ("sit on something", 10),
            ("watch a creature", 10), ("follow a creature", 9), ("take something out", 6), ("gather", 4),
            ("lay out the bits to make", 3)]
    rows = rows[::-1]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.barh([r[0] for r in rows], [r[1] for r in rows], height=0.55, color=BLUE)
    for y, (_, v) in enumerate(rows):
        ax.text(v + 0.4, y, str(v), va="center", fontsize=10.5)
    ax.set_xlim(0, 32)
    ax.set_xlabel("times chosen, out of 148 moments")
    frame(ax, "Left to choose, the model mostly wanders, looks and sits",
          "Round 9: the ten most chosen activities with no sheet at all. Making was chosen 3 times.")
    save(fig, "choices-no-sheet.png")


def before_after():
    """The live house's own log in ten-day stretches (the commit "live: the hobs think for themselves again")."""
    panels = [("Things made\nper ten world days", (230, 340), (21, 58), ""),
              ("Firsts\nper ten world days", (100, 140), (1, 11), ""),
              ("The mind's share of a\nwaking hob's time", (19, 19), (5, 5), "%"),
              ("Pride\n(0 to 100)", (63, 63), (16, 16), "")]
    fig, axes = plt.subplots(1, 4, figsize=(11, 3.9))
    for ax, (title, a, b, unit) in zip(axes, panels):
        mids = [(a[0] + a[1]) / 2, (b[0] + b[1]) / 2]
        ax.bar([0, 1], mids, width=0.5, color=[BLUE, ORANGE])
        for x, rng, mid in ((0, a, mids[0]), (1, b, mids[1])):
            if rng[0] != rng[1]:
                ax.plot([x, x], rng, color=INK, linewidth=1.5)
            label = f"{rng[0]}{unit}" if rng[0] == rng[1] else f"{rng[0]} to {rng[1]}"
            ax.text(x, max(rng) + max(a) * 0.04, label, ha="center", fontsize=10.5)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["a thought\nper action", "the body\ndecides"], fontsize=9.5)
        ax.set_ylim(0, max(a) * 1.22)
        ax.set_yticks([])
        ax.spines["bottom"].set_color(GRID)
        ax.tick_params(length=0)
        ax.set_title(title, fontsize=10.5, color=INK, pad=8)
    fig.suptitle("What happened when the model stopped choosing each action", x=0.012, y=1.27, ha="left",
                 fontsize=14, fontweight="bold")
    fig.text(0.012, 1.04, "The live house's own log. Blue: days 61 to 100, a thought for each thing a hob does.\n"
             "Orange: from day 99, a few thoughts a day and the body picks the actions.", fontsize=10.5, color=SOFT,
             linespacing=1.5, va="bottom")
    save(fig, "before-after.png")


if __name__ == "__main__":
    trait_effect()
    motive_behaviour()
    sheet_in_house()
    choices_no_sheet()
    before_after()
    print("wrote", sorted(p.name for p in OUT.glob("*.png")))
