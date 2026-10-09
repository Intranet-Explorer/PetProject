// Self-check for the voice's plans: node check-voice.ts   (no browser, no sound)
import assert from "node:assert/strict";
import { hash, planSound, planSpeech, syllables, triggers, voiceOf } from "./src/voice-plan.ts";
import type { Seen, VoiceInput } from "./src/voice-plan.ts";

const genome = { roundness: 0.72, stretch: 1.075, wobble: 0.2, hue: 31, saturation: 0.6, pattern: "speckle",
  pattern_density: 0.3, eye_size: 0.5, eye_spacing: 0.4, limbs: 0, marks: [] };
const pet = (over: Partial<VoiceInput> = {}, g = {}): VoiceInput =>
  ({ stage: "child", genome: { ...genome, ...g }, needs: { energy: 100, comfort: 60, curiosity: 50 }, ...over });
const near = (a: number, b: number, tol = 0.001) => Math.abs(a - b) <= tol * Math.max(1, Math.abs(b));

// syllables: vowel groups per word, trailing consonants stay with the last one
assert.deepEqual(syllables("something"), ["so", "me", "thing"]);
assert.deepEqual(syllables("Hello?"), ["he", "llo"]);
assert.deepEqual(syllables("hm"), ["hm"]);
assert.deepEqual(syllables("..."), []);
assert.equal(hash("llo"), hash("llo"));

// the same word sounds the same twice: same pitches, same lengths
const twice = planSpeech("hello hello", pet()).tones;
assert.equal(twice.length, 4);
assert.ok(near(twice[0].f0, twice[2].f0) && near(twice[1].f0, twice[3].f0) && near(twice[0].dur, twice[2].dur));
assert.ok(near(planSpeech("hello", pet()).tones[1].f0, planSpeech("oh hello there", pet()).tones[2].f0));
assert.ok(new Set(planSpeech("the music box tinkles softly", pet()).tones.map((n) => Math.round(n.f0))).size >= 3);   // not a monotone

// at most 24 syllables, however long the speech
assert.equal(planSpeech("la ".repeat(60), pet()).tones.length, 24);

// genome and stage to voice
const base = (stage: string, g = {}) => voiceOf(pet({ stage }, g)).base;
assert.deepEqual(["hatchling", "child", "youngling", "adult"].map((s) => Math.round(base(s))), [700, 520, 420, 330]);
assert.ok(near(base("child", { stretch: 1.4 }), 520 * 0.9) && near(base("child", { stretch: 0.75 }), 520 * 1.1));   // taller is lower
assert.deepEqual([0.9, 0.5, 0.3].map((roundness) => voiceOf(pet({}, { roundness })).timbre.wave), ["sine", "triangle", "square"]);
assert.ok(voiceOf(pet({}, { saturation: 0.2 })).timbre.cutoff < voiceOf(pet({}, { saturation: 1 })).timbre.cutoff);   // pale is muffled
assert.ok(near(voiceOf(pet({ needs: { energy: 100, comfort: 60, curiosity: 50 } })).syllable, 0.06));
assert.ok(near(voiceOf(pet({ needs: { energy: 0, comfort: 60, curiosity: 50 } })).syllable, 0.14));
assert.deepEqual([0, 1].map((wobble) => { const t = voiceOf(pet({}, { wobble })).timbre; return [t.vibratoCents, t.vibratoHz]; }), [[0, 5], [40, 7]]);
assert.equal(voiceOf(pet()).timbre.tremolo, 0);
assert.ok(voiceOf(pet({ needs: { energy: 100, comfort: 60, curiosity: 12 } })).timbre.tremolo > 0);   // any need under 20: shaky

// punctuation shapes the contour
const lastOf = (text: string, v = pet()) => planSpeech(text, v).tones.at(-1)!;
assert.ok(lastOf("are you there?").f1 > lastOf("are you there?").f0 * 1.2);        // ? rises
assert.ok(lastOf("you are there.").f1 < lastOf("you are there.").f0 * 0.85);       // . falls
const plain = planSpeech("look at this", pet()).tones, loud = planSpeech("look at this!", pet()).tones;
assert.ok(loud.every((n, i) => n.f0 > plain[i].f0 * 1.1 && n.gain > plain[i].gain));   // ! is louder and higher
const trail = planSpeech("it fades away...", pet()).tones, steady = planSpeech("it fades away", pet()).tones;
assert.ok(trail.at(-1)!.dur > steady.at(-1)!.dur * 1.5 && trail.at(-1)!.gain < steady.at(-1)!.gain * 0.5);   // ... slows and trails off
assert.ok(trail.every((n, i) => i === 0 || n.at >= trail[i - 1].at + trail[i - 1].dur));                       // and the notes still do not overlap
const pause = planSpeech("one, two", pet()).tones, none = planSpeech("one two", pet()).tones;
assert.ok(pause.at(-1)!.at - pause.at(-2)!.at > none.at(-1)!.at - none.at(-2)!.at + 0.1);                         // a comma is a longer gap

// how it is shapes the phrase
const eager = pet({ needs: { energy: 100, comfort: 60, curiosity: 90 } }), sad = pet({ needs: { energy: 100, comfort: 20, curiosity: 50 } });
assert.ok(lastOf("look at this", eager).f1 > lastOf("look at this", eager).f0);    // curious: ends up
assert.equal(lastOf("look at this").f1, lastOf("look at this").f0);
const low = planSpeech("la la la la", sad).tones, well = planSpeech("la la la la", pet()).tones;
assert.ok(low[0].f0 < well[0].f0 && low[3].f0 < low[0].f0 && well[3].f0 === well[0].f0);   // uncomfortable: lower, and drifting down

// sounds without words come from the same voice
for (const kind of ["cry", "chirp", "blip", "trill", "stageup", "hm", "whimper"] as const) {
  const child = planSound(kind, pet({ stage: "child" })), adult = planSound(kind, pet({ stage: "adult" }));
  assert.ok(child.tones.length > 0 && child.length > 0.05 && child.length < 1.2, kind);
  assert.ok(near(child.tones[0].f0 / adult.tones[0].f0, 520 / 330), kind);       // a bigger body is lower, in every sound
}
assert.ok(planSound("cry", pet()).tones[0].f1 > planSound("cry", pet()).tones[0].f0 * 2);         // a rising squeak
assert.ok(planSound("blip", pet()).tones[0].f1 < planSound("blip", pet()).tones[0].f0);           // falling
const up = planSound("stageup", pet()).tones;
assert.ok(up.length === 3 && up[0].f0 < up[1].f0 && up[1].f0 < up[2].f0);                           // three rising notes

// triggers: what in a snapshot calls for a sound. Nothing on the first look.
const world = (over = {}) => ({ pet: { said: null as [number, string] | null, stage: "child" }, moments: [] as [number, string][],
  events: [] as [number, string][], objects: {}, sleep: null as unknown, ...over });
const first = triggers(null, world({ moments: [[5, "it made a soft cloud"]], pet: { said: [4, "hi"], stage: "child" } }), [], []);
assert.ok(first.speak === null && first.sounds.length === 0);
const after = (w: ReturnType<typeof world>, journal: Parameters<typeof triggers>[2] = [], things: Parameters<typeof triggers>[3] = [], seen: Seen = first.seen) =>
  triggers(seen, w, journal, things);
const kept = { moments: [[5, "it made a soft cloud"]] as [number, string][], pet: { said: [4, "hi"] as [number, string], stage: "child" } };
assert.deepEqual(after(world(kept)).sounds, []);                                                      // nothing new, nothing played
assert.equal(after(world({ ...kept, pet: { said: [9, "Look at this!"], stage: "child" } })).speak, "Look at this!");
const says = (text: string) => after(world({ ...kept, moments: [...kept.moments, [9, text]] })).sounds;
assert.deepEqual(says("it hatched"), ["cry"]);
assert.deepEqual(says("it made a dim stone"), ["chirp"]);
assert.deepEqual(says("it combined the a and the b into a c"), ["chirp"]);
assert.deepEqual(says("it took apart the dim stone"), ["blip"]);
assert.deepEqual(says("it is now a Youngling"), ["stageup"]);
assert.deepEqual(says("it now has a small notch"), []);
const visit = (text: string) => after(world({ ...kept, events: [[9, text]] })).sounds;
assert.deepEqual(visit('visitor said "hello!"'), ["hm"]);
assert.deepEqual(visit("visitor poked you"), ["hm"]);
assert.deepEqual(visit("visitor filled the bowl"), []);
assert.deepEqual(visit("you rested; energy +8.0"), []);
const use = (target: string, own: object, extra = {}) => [{ type: "step", tick: 9, action: { type: "use", target }, reason: null, own, ...extra }];
assert.deepEqual(after(world(kept), use("blanket", { comfort: 2 })).sounds, ["trill"]);              // a use that helped
assert.deepEqual(after(world(kept), use("rock", { curiosity: 0.4 })).sounds, []);                    // one that did nothing
assert.deepEqual(after(world(kept), use("rattle", { curiosity: 3 }), [{ name: "rattle", ups: 1 }]).sounds, ["trill"]);   // the engine counted it as a help
assert.deepEqual(after(world(kept), use("bed", { energy: 3 }, { reason: "bad target" })).sounds, []);
const many = after(world({ ...kept, moments: [...kept.moments, [9, "it took apart the x"], [9, "it is now a Child"]], events: [[9, "visitor poked you"]] }));
assert.deepEqual(many.sounds, ["stageup", "blip", "hm"]);                                             // the bigger news first
const amb = after(world({ ...kept, sleep: { since: 3 }, pet: { said: null, stage: "egg" },
  objects: { drone: { active: true, made: { behavior: { do: "hum" } } }, lantern: { active: true, made: { behavior: { do: "glow" } } }, still: { active: false, made: { behavior: { do: "hum" } } } } })).ambient;
assert.deepEqual(amb, { egg: true, asleep: true, hums: ["drone"] });

console.log("voice check ok");
