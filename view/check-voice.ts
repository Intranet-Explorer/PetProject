// Self-check for the voice's plans: node check-voice.ts   (no browser, no sound)
import assert from "node:assert/strict";
import { hash, news, planSong, planSound, planSpeech, semitone, syllables, voiceOf } from "./src/voice-plan.ts";
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

// phase 2: talking grows with the stage, and elders are lower, slower and tremble
assert.equal(planSpeech("hello there", pet({ stage: "egg" })).tones.length, 0);                    // an egg only has a heartbeat
const peep = planSpeech("what is this thing?", pet({ stage: "hatchling" })).tones;
assert.equal(peep.length, 4);                                                                         // a hatchling: one chirp a word, no babble
assert.ok(peep.every((n) => n.f0 > 700) && peep.at(-1)!.f1 > peep.at(-1)!.f0 * 1.2);                  // high, and a question still rises
assert.ok(planSpeech("something wonderful happened", pet({ stage: "child" })).tones.length > 3);              // a child babbles every syllable
assert.equal(Math.round(base("elder")), 290);
assert.ok(voiceOf(pet({ stage: "elder" })).syllable > voiceOf(pet({ stage: "adult" })).syllable * 1.3 && voiceOf(pet({ stage: "elder" })).timbre.tremolo > 0);
const talk = planSpeech("hello Moss, the soft nest is warm", pet({ stage: "youngling", words: ["Moss", "soft nest"] }));
assert.deepEqual(talk.words!.map((w) => w.word), ["hello", "moss", "soft", "nest"]);                 // real words come through the babble
assert.ok(talk.tones.length === 3 && talk.words!.every((w, i, all) => i === 0 || w.at > all[i - 1].at));   // "the", "is", "warm" stay babble
assert.equal(planSpeech("hello Moss", pet({ stage: "child", words: ["Moss"] })).words!.length, 0);    // not before youngling
const parent = voiceOf(pet({ stage: "adult" }, { stretch: 1.3, roundness: 0.9 })), child = voiceOf(pet({ stage: "adult" }, { stretch: 1.27, roundness: 0.86 }));
const stranger = voiceOf(pet({ stage: "adult" }, { stretch: 0.8, roundness: 0.3 }));
assert.ok(Math.abs(parent.base - child.base) < 5 && parent.timbre.wave === child.timbre.wave && stranger.timbre.wave !== parent.timbre.wave);   // a family sounds alike
assert.ok(planSound("last", pet()).tones.at(-1)!.f1 < planSound("last", pet()).tones[0].f0);         // a death goes down and out

// news: what in a snapshot calls for a sound, and whose. Nothing on the first look.
const snap = (over = {}) => ({ tick: 10, pets: [{ id: "p1", room: "r11", said: { text: "hi", tick: 4 } }, { id: "p2", room: "r10", said: null }],
  moments: [{ n: 1, kind: "made", pet: "p1", room: "r11" }], ...over });
const first = news(null, snap());
assert.ok(first.speak.length === 0 && first.sounds.length === 0 && first.house.length === 0);
assert.deepEqual(news(first.seen, snap()).speak, []);                                                 // nothing new, nothing played
const spoke = news(first.seen, snap({ pets: [{ id: "p1", room: "r11", said: { text: "hi", tick: 4 } }, { id: "p2", room: "r10", said: { text: "hello mother", tick: 9 } }] }));
assert.deepEqual(spoke.speak, [{ pet: "p2", text: "hello mother" }]);                                 // each pet's speech is its own
const more = news(first.seen, snap({ moments: [{ n: 1, kind: "made", pet: "p1", room: "r11" }, { n: 2, kind: "hatched", pet: "p2", room: "r10" },
  { n: 3, kind: "power", pet: null, room: null }, { n: 4, kind: "death", pet: "p1", room: "r11" }, { n: 5, kind: "season", pet: null, room: null }] }));
assert.deepEqual(more.sounds.map((x) => [x.kind, x.pet, x.room]), [["cry", "p2", "r10"], ["last", "p1", "r11"]]);
assert.deepEqual(more.house, [{ kind: "powerdown", room: null }]);

// SPEC-v3.1 §3.4: a song is the singer's own voice holding the notes of a five-note scale; each one sung is heard once
assert.deepEqual(["low do", "low la", "do", "re", "mi", "so", "la", "high do", "high la"].map(semitone), [-12, -3, 0, 2, 4, 7, 9, 12, 21]);
const tune: [string, number][] = [["mi", 0], ["so", 0], ["la", 1], ["high do", 0]], sung = planSong(tune, pet({ stage: "adult" }));
assert.ok(sung.tones.length === 4 && sung.tones.every((n) => n.f0 === n.f1));                                   // held, not bent
assert.ok(near(sung.tones[0].f0, base("adult") * 2 ** (4 / 12)) && near(sung.tones[3].f0 / sung.tones[0].f0, 2 ** (8 / 12)));   // "do" is where it speaks
assert.ok(near(sung.tones[2].dur, 2 * sung.tones[0].dur) && sung.tones.every((n, i) => i === 0 || n.at >= sung.tones[i - 1].at + sung.tones[i - 1].dur));   // a long note is twice a short one
assert.ok(near(planSong(tune, pet({ stage: "child" })).tones[0].f0 / sung.tones[0].f0, 520 / 330));             // the same song, higher in a child
assert.ok(planSong(tune, pet({ stage: "elder" })).length > sung.length && sung.timbre.wave === voiceOf(pet({ stage: "adult" })).timbre.wave);
const quiet = news(null, snap({ sung: [{ tick: 9, by: "p1", song: "s1", room: "r11" }], radio: { said: [{ tick: 8, room: "r11", source: "weather", text: "rain" }] } }));
assert.ok(quiet.sing.length === 0 && quiet.heard.length === 0);                                                // old news on the first look
const later = snap({ sung: [{ tick: 9, by: "p1", song: "s1", room: "r11" }, { tick: 10, by: "p2", song: "s1", room: "r11" }, { tick: 10, by: "music box", song: "s2", room: "r11" }],
  radio: { said: [{ tick: 8, room: "r11", source: "weather", text: "rain" }, { tick: 10, room: "r11", source: "", text: "" }] },
  pets: [{ id: "p1", room: "r11", said: { text: "♪ the cellar song", tick: 10, song: "s1" } }] });
const heard = news(quiet.seen, later);
assert.deepEqual([heard.sing.map((x) => x.by), heard.heard.map((x) => x.text), heard.speak], [["p2", "music box"], [""], []]);   // each once, static too; a song is not also babbled
assert.ok(news(heard.seen, later).sing.length === 0 && news(first.seen, snap()).sing.length === 0);            // not again; and a recording without the new fields is fine
assert.equal(news(first.seen, snap({ moments: [{ n: 2, kind: "arrival radio", pet: null, room: "r00" }] })).house[0].kind, "tuning");   // a discovery has its own sound

console.log("voice check ok");
