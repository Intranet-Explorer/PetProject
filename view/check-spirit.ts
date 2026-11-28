// Self-check for the page's spirit (SPEC-v4.2 §11, §12 E: the bubbles and the card with fake data): node check-spirit.ts
import assert from "node:assert/strict";
import { cardRows, mindsOf, talkOf, thoughtOf } from "./src/spirit.ts";
import { DECLINE, declineOf } from "./src/pet.ts";
import { deathMark } from "./src/pages/tree.ts";
import type { PetV, Talk } from "./src/types.ts";

// §11.1 a plan's or a reaction's thought is a cloud of its own; nothing with v4.2 off, asleep, for a design, or dead
const plan = (why: string, thought: string) => ({ intention: "", thought, expect: "", i: 0, why, steps: [], acting: false });
const hob = (o: Partial<PetV> = {}) => ({ stage: "adult", asleep: false, plan: plan("plan", "The roof waits; the clay is in the storeroom."), ...o }) as Pick<PetV, "stage" | "asleep" | "plan">;
assert.deepEqual(thoughtOf(hob(), true), { key: "plan|The roof waits; the clay is in the storeroom.", text: "The roof waits; the clay is in the storeroom." });
assert.equal(thoughtOf(hob({ plan: plan("react", "Eirlys is crying.") }), true)?.text, "Eirlys is crying.");
assert.notEqual(thoughtOf(hob(), true)!.key, thoughtOf(hob({ plan: plan("plan", "Another day.") }), true)!.key);   // a new thought, a new cloud
for (const off of [thoughtOf(hob(), false), thoughtOf(hob({ asleep: true }), true), thoughtOf(hob({ plan: plan("design", "a lamp") }), true),
  thoughtOf(hob({ stage: "dead" }), true), thoughtOf(hob({ plan: plan("plan", "  ") }), true), thoughtOf(hob({ plan: null }), true)]) assert.equal(off, null);

// a talk's wants and holds, by hob, when the talk is clicked: its latest in this room that left minds
const talk = (n: number, room: string, minds?: Talk["minds"]): Talk => ({ n, tick: n, room, a: "p1", b: "p2", lines: [{ who: "p1", text: "hello" }], minds });
const side = (wants: string, holds: string) => ({ wants, holds, knows: "", remember: "" });
const t = talk(3, "r1", { p1: side("to be forgiven", "that I broke the cup"), p2: side("", "") });
assert.deepEqual(mindsOf(t), { p1: "wants: to be forgiven / keeps back: that I broke the cup" });   // (a side with neither has no cloud)
assert.deepEqual(mindsOf(talk(1, "r1")), {});
const talks = [talk(1, "r1", { p1: side("the clay", "") }), t, talk(4, "r2", { p1: side("elsewhere", "") }), talk(5, "r1")];
assert.equal(talkOf(talks, "r1", "p1")?.n, 3);      // the latest here with minds (5 has none, 4 is in another room)
assert.equal(talkOf(talks, "r1", "p9"), null);
assert.equal(talkOf(undefined, "r1", "p1"), null);

// §11.2 the card: its rows; a secret is only "keeps something to itself" until found out, whatever else is sent
const card = { self: ["who I am: a maker of bowls"], drive: "to be loved by one (Wen)", flaw: "proud", voice: 'speaks terse, says "well" too often',
  theory: "the visitor is the one who feeds us", taught: "taught: fishing", secret: { found: false, text: "I took the blue feather" } };
const rows = Object.fromEntries(cardRows(card));
assert.deepEqual(rows, { Drive: "to be loved by one (Wen)", Flaw: "proud", Voice: 'speaks terse, says "well" too often', "Of you": "the visitor is the one who feeds us",
  Taught: "fishing", Secret: "keeps something to itself" });
assert.ok(!JSON.stringify(cardRows(card)).includes("feather"), "never the secret's words before it is found out");
assert.equal(Object.fromEntries(cardRows({ ...card, secret: { found: true, text: "I took the blue feather" } })).Secret, "found out: I took the blue feather");
assert.deepEqual(cardRows({}), []);
assert.deepEqual(cardRows(undefined), []);
assert.deepEqual(cardRows({ leave: { what: "my blue cup", to: "Wen" } }), [["Would leave", "my blue cup to Wen"]]);
assert.deepEqual(cardRows({ threads: ["with Wen, about the box (where it went)"] }), [["Left open", "with Wen, about the box (where it went)"]]);   // SPEC-v5.3 §8

// §11.3 decline: every stage of sickness (contracts.SICK) has its look; old and slow stoops; a poisonous catch shows nothing
assert.deepEqual(Object.keys(DECLINE), ["unwell", "ill", "gravely ill"]);
const none = { pale: false, bed: false, down: false, stoop: false };
assert.deepEqual(declineOf({ stage: "adult", sick: { level: "unwell" } }, true), { ...none, pale: true });
assert.deepEqual(declineOf({ stage: "adult", sick: { level: "ill" } }, true), { ...none, pale: true, bed: true });
assert.deepEqual(declineOf({ stage: "child", sick: { level: "gravely ill" } }, true), { pale: true, bed: true, down: true, stoop: false });   // (children are hobs: §2)
assert.deepEqual(declineOf({ stage: "elder", old: true }, true), { ...none, stoop: true });
assert.deepEqual(declineOf({ stage: "adult", old: true }, true), none);              // ("old and slow" is an elder's)
assert.deepEqual(declineOf({ stage: "adult", sick: { level: "ill" } }, false), none); // v4.2 off: v4.0.6's look only
assert.deepEqual(declineOf({ stage: "dead", sick: { level: "ill" } }, true), none);
assert.deepEqual(declineOf({ stage: "adult", sick: null }, true), none);             // carrying the red-finned fish: no mark

// §11.4 the tree marks a death not of age, its cause the title
assert.equal(deathMark({ alive: false, of_age: false, cause_words: "died of the cold, untended" }), "died of the cold, untended");
assert.equal(deathMark({ alive: false, of_age: true, cause_words: "died of old age" }), null);
assert.equal(deathMark({ alive: true }), null);
assert.equal(deathMark({ alive: false }), null);   // (v4.2 off: the engine sends no words)
console.log("spirit check ok");
