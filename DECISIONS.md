# Decisions

Where the build departs from [SPEC-v3.md](SPEC-v3.md), or settles something the spec leaves open: what the spec
said, what was done, and the evidence. Newest at the bottom of each part. (The v1 and v2 departures are in
README.md's history and NOTES.md.)

## Part 0: closing v2.5

- **The parent's message was cut to its last whole sentence.** The spec says at most 600 characters. The
  constrained output stopped the reply at exactly 600, mid-sentence ("I rested near the calm and"). The egg is
  given the 573 characters up to "…the breathing moon." The full reply is kept in
  `data.v2.5/baseline/message.json`. From now on the message schema allows a little over the limit and the
  engine trims to the last whole sentence inside it, so a parent's words never end on half a thought.
- **The message was asked with thinking on.** Every other waking call in v2 had thinking off. This was one
  call that a whole lineage starts from, and M0 found the model writes better with it.
- **The mother has no name, so she is "the first one".** Asked what it calls itself, the pet left it empty.
- **The first v3 egg also gets her body.** The spec passes on only the message. The egg will be laid with the
  v2.5 pet's final genome and one round of mutation, as §5.4 does for every later egg, so the lineage's bodies
  and voices begin from her and not from the default. Her temperament was never measured, so the first
  egg's is drawn at random from the house's seed.
- **More was saved than asked.** Beliefs, the last five dreams and Things, as the spec says, plus her final
  state, her two self-portraits, her moments, and her meter-talk figure (25.2% of 765 thoughts, 57.9% of 19
  beliefs), which §12 wants beside v3's.
- **"character" and "agent" were never in a prompt.** Checked across all 812 prompts of the v2.5 life, outside
  her own beliefs, dreams and speech: zero. Her calling herself "the character", "the agent" and "the entity"
  was her own. That goes in FINDINGS.md when it is next updated.
