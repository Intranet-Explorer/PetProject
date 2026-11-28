// Self-check for a conversation's timing in the room (SPEC-v4.0 §5, §11): node check-talk.ts
import assert from "node:assert/strict";
import { lineAt, lineMs, PAUSE, roundStarts, talkMs } from "./src/px/talk.ts";

const lines = [{ who: "a", text: "hi" }, { who: "b", text: "x".repeat(200) }, { who: "a", text: "bye" }];
assert.equal(lineMs("hi"), 2600);                          // a short line is up long enough to read
assert.equal(lineMs("x".repeat(200)), 5200);               // a long one no longer than five seconds
assert.deepEqual(lineAt(lines, 0), { i: 0, left: 2600 });
assert.equal(lineAt(lines, 2600), null);                   // the pause between lines
assert.deepEqual(lineAt(lines, 2600 + PAUSE), { i: 1, left: 5200 });
assert.equal(lineAt(lines, 2600 + PAUSE + 5200 + PAUSE + 100)?.i, 2);
assert.equal(lineAt(lines, talkMs(lines)), null);          // all said
// SPEC-v5.3 §8: a talk that went on shows its rounds as one conversation, divided where each round begins
assert.deepEqual(roundStarts({ rounds: [lines, lines.slice(0, 2), lines] }), [3, 5]);
assert.deepEqual(roundStarts({ rounds: [lines] }), []);
assert.deepEqual(roundStarts({}), []);
console.log("talk check ok");
