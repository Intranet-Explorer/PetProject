// Self-check for the house's sound, as plans: node check-voice.ts   (no browser, no sound)
// sounds.json against itself and the files, the levels, babble, the gate on repeats, what music and ambience a room
// wants, what in a snapshot calls for a sound, and the songs in a hob's own voice.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { babble, filesOf, Gate, gainOf, levelOf, news, planSong, rings, semitone, soundFor, voiceOf, wantAmbience, wantMusic } from "./src/voice-plan.ts";
import type { Sounds, VoiceInput } from "./src/voice-plan.ts";

const ASSETS = new URL("./assets/", import.meta.url);
const S: Sounds = JSON.parse(readFileSync(new URL("sounds.json", ASSETS), "utf8"));
const near = (a: number, b: number, tol = 0.001) => Math.abs(a - b) <= tol * Math.max(1, Math.abs(b));

// ---- sounds.json: every name it uses is a sound of ours, every sound's group has a level, every file is there ----
const names = new Set(Object.keys(S.sounds)), used: string[] = [];
const walk = (x: unknown): void => { if (typeof x === "string") used.push(x); else if (Array.isArray(x)) x.forEach(walk); else if (x && typeof x === "object") Object.values(x).forEach(walk); };
walk([S.music.day, S.music.night, S.music.winter, S.music.outdoors, S.music.rooms, S.music.moods, S.music.visitor, S.ambience.rooms, S.ambience.weather, S.floors, S.on]);
assert.deepEqual(used.filter((n) => !names.has(n)), [], "names sounds.json uses that are not in its sounds");
for (const [n, e] of Object.entries(S.sounds)) assert.ok(e.group in S.groups, `${n}: no group ${e.group}`);
assert.deepEqual(Object.fromEntries(["footsteps", "hands", "making", "creatures", "ui", "voices", "machines", "jingles", "conflict"].map((g) => [g, S.groups[g]])),
  { footsteps: -14, hands: -8, making: -6, creatures: -6, ui: -10, voices: -3, machines: -8, jingles: 0, conflict: 0 });   // the lead's levels (18 October 2026)
const wavs = [...names].flatMap((n) => filesOf(S, n));
if (existsSync(new URL("audio/music/house_day.wav", ASSETS))) assert.deepEqual(wavs.filter((f) => !existsSync(new URL(f, ASSETS))), [], "files sounds.json names that are not there");
assert.equal(wavs.length, 233);   // every file of the set is a sound of ours
assert.deepEqual(filesOf(S, "sfx/step_wood"), ["audio/sfx/step_wood_1.wav", "audio/sfx/step_wood_2.wav", "audio/sfx/step_wood_3.wav"]);
assert.deepEqual(filesOf(S, "sfx/hop"), ["audio/sfx/hop.wav"]);
assert.deepEqual(filesOf(S, "nope"), []);
assert.ok(near(levelOf(S, "sfx/step_wood")!.gain, gainOf(-14)) && levelOf(S, "sfx/step_wood")!.bus === "effects");
assert.deepEqual(["music/house_day", "ambience/cellar", "sfx/voice_babble", "ui/click"].map((n) => levelOf(S, n)!.bus), ["music", "ambience", "voices", "effects"]);
assert.ok(levelOf(S, "ambience/cellar")!.loop && levelOf(S, "sfx/kiln_fire")!.loop && !levelOf(S, "sfx/hop")!.loop && !levelOf(S, "music/house_day")!.loop);   // music plays once, then rests
assert.ok(!JSON.stringify(S).includes("synth") && !JSON.stringify(S).includes("pitch"));   // no sound made in the page: the hum cannot come back
assert.equal(soundFor(S, "act.gather"), "sfx/gather");
assert.equal(soundFor(S, "no such thing"), null);
assert.ok(["sfx/sneeze", "sfx/cough"].includes(soundFor(S, "sick")!));   // a list: one of them

// ---- the gate on repeats: the same sound in the same room at most once in 1 to 2 s; others are free ----
const gate = new Gate([1, 2], () => 0.5);
assert.deepEqual([gate.open("step|r1", 10), gate.open("step|r1", 10.9), gate.open("step|r2", 10.9), gate.open("hop|r1", 10.9), gate.open("step|r1", 11.6)], [true, false, true, true, true]);
assert.deepEqual([gate.open("sleep|p1", 0, 6), gate.open("sleep|p1", 5), gate.open("sleep|p1", 6.1)], [true, false, true]);

// ---- babble: a syllable every few letters, pitched to the body, ±5% each; ? rises, ! is louder; at most 14 ----
const genome = { roundness: 0.72, stretch: 1.075, wobble: 0.2, hue: 31, saturation: 0.6, pattern: "speckle", pattern_density: 0.3, eye_size: 0.5, eye_spacing: 0.4, limbs: 0, marks: [] };
const pet = (stage: string, g = {}): VoiceInput => ({ stage, genome: { ...genome, ...g }, needs: { energy: 100, comfort: 60, curiosity: 50 } });
const base = (stage: string) => voiceOf(pet(stage)).base;
const flat = () => 0.5;   // no randomness: the middle of every range
assert.deepEqual(["hatchling", "child", "youngling", "adult", "elder"].map((s) => Math.round(base(s))), [700, 520, 420, 330, 290]);
assert.ok(near(voiceOf(pet("child", { stretch: 1.4 })).base, 520 * 0.9));   // taller is lower
assert.equal(babble("hello there", base("egg"), "egg").length, 0);
assert.equal(babble("what is this thing?", base("hatchling"), "hatchling", 8, flat).length, 4);   // a hatchling: one peep a word
const child = babble("hello there, how are you", base("child"), "child", 8, flat), adult = babble("hello there, how are you", base("adult"), "adult", 8, flat);
assert.ok(child.length >= 5 && child.length === adult.length && child[0].rate > adult[0].rate);   // a child is higher
assert.ok(child.every((x, i) => i === 0 || x.at > child[i - 1].at));
assert.equal(babble("la ".repeat(60), base("child"), "child").length, 14);
const q = babble("are you there?", base("adult"), "adult", 8, flat), plain = babble("are you there", base("adult"), "adult", 8, flat);
assert.ok(near(q.at(-1)!.rate, plain.at(-1)!.rate * 1.12) && babble("look!", base("adult"), "adult", 8, flat)[0].gain > plain[0].gain);
for (const x of babble("the music box tinkles softly by the window", base("adult"), "adult")) assert.ok(Math.abs(x.rate / babble("a", base("adult"), "adult", 8, flat)[0].rate - 1) <= 0.0501 && x.v >= 0 && x.v < 8);
const [one, two] = [babble("one, two", base("adult"), "adult", 8, flat), babble("one two", base("adult"), "adult", 8, flat)];
assert.ok(one.at(-1)!.at > two.at(-1)!.at + 0.1);   // a comma is a longer gap
assert.ok(babble("a long while", base("elder"), "elder", 8, flat).at(-1)!.at > babble("a long while", base("adult"), "adult", 8, flat).at(-1)!.at);   // an elder is slower

// ---- music: a mood takes over; else a storm, the room's theme, outdoors or the house by day or night ----
const M = (o: Partial<Parameters<typeof wantMusic>[1]>) => wantMusic(S, { mood: null, type: "workshop", phase: "day", season: "spring", weather: "clear", ...o });
assert.deepEqual(M({ mood: "fight" }), { name: "music/fight", take: true });
assert.deepEqual(M({ type: "nursery" }), { name: "music/nursery", take: false });
assert.equal(M({ type: "music" }), null);   // the music room plays only the hobs' own songs
assert.equal(M({ type: "storeroom" })!.name, "music/house_day");
assert.equal(M({ type: "storeroom", phase: "dusk" })!.name, "music/house_night");
assert.equal(M({ type: "storeroom", season: "winter" })!.name, "music/winter");
assert.equal(M({ type: "yard", phase: "night" })!.name, "music/outdoors_night");
assert.equal(M({ weather: "storm", type: "nursery" })!.name, "music/storm");
assert.equal(M({ mood: "grief", weather: "storm" })!.name, "music/grief");

// ---- ambience: the room's (its night file after dark), the weather on top as far as the room hears the sky; at most three ----
const A = (type: string, phase: string, weather: string) => wantAmbience(S, type, phase, weather);
assert.deepEqual(A("nursery", "night", "clear"), [{ name: "ambience/nursery_night", gain: 1, roof: false }]);
assert.deepEqual(A("cellar", "night", "clear").map((x) => x.name), ["ambience/cellar"]);
const rain = A("nursery", "day", "rain"), cellar = A("cellar", "day", "rain"), yard = A("yard", "day", "storm");
assert.ok(rain[1].name === "ambience/rain_roof" && rain[1].roof && rain[1].gain < 1 && cellar[1].gain < rain[1].gain);   // through the roof, quieter shut in
assert.deepEqual(yard.map((x) => [x.name, x.gain, x.roof]), [["ambience/yard", 1, false], ["ambience/rain_ground", 1, false], ["ambience/wind_strong", 1, false]]);
assert.ok(A("attic", "day", "rain")[1].gain === 1 && A("nursery", "day", "snow").length === 1);
for (const t of Object.keys(S.ambience.rooms)) for (const w of ["clear", "rain", "storm", "snow", "heat"]) assert.ok(A(t, "night", w).length <= 3);

// ---- news: what in a snapshot calls for a sound, and whose. Nothing on the first look ----
const snap = (over = {}) => ({ tick: 10, pets: [{ id: "p1", room: "r11", said: { text: "hi", tick: 4 } }, { id: "p2", room: "r10", said: null }],
  moments: [{ n: 1, kind: "made", pet: "p1", room: "r11" }], ...over });
const first = news(null, snap());
assert.ok(first.speak.length === 0 && first.moments.length === 0);
const spoke = news(first.seen, snap({ pets: [{ id: "p1", room: "r11", said: { text: "hi", tick: 4 } }, { id: "p2", room: "r10", said: { text: "hello mother", tick: 9, to: "visitor" } }] }));
assert.deepEqual(spoke.speak, [{ pet: "p2", text: "hello mother", to: "visitor" }]);
const more = news(first.seen, snap({ moments: [{ n: 1, kind: "made", pet: "p1", room: "r11" }, { n: 2, kind: "hatched", pet: "p2", room: "r10" }, { n: 3, kind: "killing", pet: "p1", room: "r11" }] }));
assert.deepEqual(more.moments.map((m) => m.kind), ["hatched", "killing"]);
assert.ok(news(more.seen, snap({ tick: 11, moments: [{ n: 3, kind: "killing", pet: "p1", room: "r11" }] })).moments.length === 0);   // each once
const later = snap({ sung: [{ tick: 9, by: "p1", song: "s1", room: "r11" }, { tick: 10, by: "p2", song: "s1", room: "r11" }], pets: [{ id: "p1", room: "r11", said: { text: "♪ the cellar song", tick: 10, song: "s1" } }] });
const quiet = news(null, snap({ sung: [{ tick: 9, by: "p1", song: "s1", room: "r11" }] })), heard = news(quiet.seen, later);
assert.deepEqual([heard.sing.map((x) => x.by), heard.speak], [["p2"], []]);   // a song is played once, and not also babbled
const vox = [{ n: 3, pet: "p1", room: "r11", kind: "yawn" }], v1 = news(first.seen, snap({ vox }));
assert.deepEqual([news(null, snap({ vox })).vox.length, v1.vox.map((x) => x.kind), news(v1.seen, snap({ vox })).vox.length], [0, ["yawn"], 0]);
assert.equal(news(first.seen, snap({ tick: 100, tick_seconds: 2 })).moments.length, 0);   // a jump in time: listening afresh

// ---- SPEC-v3.6b §4: the anvil rings only in the room on screen, only while the forge works, a few seconds apart at least ----
const forge = (state: string) => ({ rooms: [{ id: "r20", objects: { forge: { machine: { kind: "forge", state } } } }] });
assert.deepEqual([rings(forge("working"), "r20", 10, 0), rings(forge("working"), "r02", 10, 0), rings(forge("cold"), "r20", 10, 0), rings(forge("working"), "r20", 10, 8)], [true, false, false, false]);

// ---- SPEC-v3.1 §3.4: a song is the singer's own voice holding the notes of a five-note scale ----
assert.deepEqual(["low do", "low la", "do", "re", "mi", "so", "la", "high do", "high la"].map(semitone), [-12, -3, 0, 2, 4, 7, 9, 12, 21]);
const tune: [string, number][] = [["mi", 0], ["so", 0], ["la", 1], ["high do", 0]], sung = planSong(tune, pet("adult"));
assert.ok(sung.tones.length === 4 && sung.tones.every((n) => n.f0 === n.f1));
assert.ok(near(sung.tones[0].f0, base("adult") * 2 ** (4 / 12)) && near(sung.tones[2].dur, 2 * sung.tones[0].dur));
assert.ok(near(planSong(tune, pet("child")).tones[0].f0 / sung.tones[0].f0, 520 / 330) && planSong(tune, pet("elder")).length > sung.length);

console.log("voice check ok");
