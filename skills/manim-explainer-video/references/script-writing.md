# Writing the script

Read this before writing any narration. It comes from two finished videos that the user rejected for the writing, not the pictures: "they don't feel like they're written by a human", "no story", "not easier to read", "no spacing", and visuals "too oversimplified to present a good visual explanation".

The test for every paragraph: could a good engineer say this, out loud, to one person across a table, without it sounding read? If not, rewrite it.

## 1. One concrete system is the spine

Pick one real, specific system and keep it on screen and in the narration for the whole video. Establish the system, the task and the visible consequence in the opening; introduce each parameter when it helps answer the current question, and keep the rest in the model notes.

> Say we have a spacecraft with an 80 kilogram bus. It has a 5 meter boom with a 2 kilogram payload at the tip. A star tracker on that bus has to hold its line of sight. Line of sight of what? ...

- Every new idea is met on that system first, then named as a general rule. The general rule is said once the example has forced it, in one sentence.
- Do not swap the system for a metaphor (a spring, a swing, a child on a playground) and stay there. An analogy may introduce an idea for one or two sentences; then come back to the real hardware and show the same thing on it.
- Each major explanation connects the example to a principle that transfers, said where it helps, not repeated mechanically in every scene. A reduced model (a two-mass sketch, a block diagram) is fine when its parts stay visibly mapped to the hardware. A middle that only teaches how to present the answer to one problem is overfitting.

## 2. One causal arc, with ideas met as problems before they are named

Build the video around one consequential engineering question. The default shape for a major idea is below; use it where it clarifies the mechanism, not for every beat. Some beats just measure, compare or establish a limit, and forcing a theatrical failure into each one reads as manufactured.

1. **Ideal.** What we want, on this system, with the number. "We command a 30 degree slew and want the tracker steady within a tenth of a degree."
2. **Breaks.** Reality gets in the way, on the same system. "The bus stops. The boom doesn't."
3. **Naive fix, and why it fails.** Try the obvious thing and let the viewer watch it fail. "So just make the controller faster? Here's what happens..."
4. **Named technique.** Only now name the concept (bandwidth, gain stabilization, collocation, Nyquist) as the answer to the failure the viewer just felt.

Terms and rules come after the need for them is clear. A definition may open a scene when the previous beat created the need for it; it never comes before the viewer knows what it is for. Do not sort or classify things ("three frequencies: which is structure, which is control?") before the viewer has a reason to care.

One question leads to the next. Do not open a new topic until the last step raised it. A good link sentence is the question the viewer would ask next: "Okay, but why does a tenth of a second matter at all?"

## 3. Resolve the listener's question when it arises

State the assumed audience (for example: an engineer outside this specialty). When a phrase would leave that listener asking "of what?" or "meaning what?", resolve it right there: ask it aloud when that sounds natural (the user likes this), otherwise answer it directly in the narration or the picture.

> A star tracker is a small camera that matches the star pattern it sees against a catalog, so the craft knows which way it is pointing. It isn't looking at the ground. The camera looking at the ground sits on the same bus, so when the bus nods, that picture walks.

Explain an unfamiliar term when the current inference needs it, usually with a short phrase and something visible to point at (slew, reaction wheel, root fitting, damping, loop gain, bandwidth, node). Defer the rest. Never stop the action for a glossary: a rewrite that explained the tracker, ground camera, pointing requirement, slew, root fitting and reaction wheel before the craft had even turned was an overcorrection.

## 4. Sentences: complete spoken thoughts

- Vary length around complete spoken thoughts. Measured on caption transcripts: 3Blue1Brown runs 25 to 28 words a sentence with 1 to 4% under six words, Marshall Bruner about 20 with 8%; the rejected scripts averaged about 10 with 18 to 42%. If the project has reference transcripts, read two of them before writing. The lint statistics only point you at passages to listen to; never join sentences with commas to pass them, which just trades slogans for rambling.
- No fragments or slogans standing in for an explanation: "The boom doesn't." is fine once as a beat; "Quick check. About 93 minutes." and "Same craft. Same command. Opposite motion." in a row are not. At most about 1 sentence in 7 under 6 words.
- Each paragraph explains a relationship, and connectives (so, but, because, which means, here's the thing) make the link explicit. A connective only counts when the clauses really are linked; a decorative "so" fixes nothing.
- Contractions and plain words: "it's", "doesn't", "we", "you". Say "we" for the designer and "you" for the listener.
- No narrator stage directions ("Keep your answer.", "Remember that.", "Let's build each."). Just continue the explanation.
- Name the thing; do not open a sentence with a bare It, That, This, These or Those followed by a verb ("That's roughly a seventh of the satellite", "It adds more time"). A listener cannot scroll back. Say "The thruster's propellant is roughly a seventh..." or "The three-part shaper adds more time". "That tilt" (pronoun plus noun) is fine.
- Match the tense to when the thing happened. A design choice already made is past or present perfect ("we biased the wheels away from zero speed", "we have set the mount at 3.3 hertz"); present simple is for what is true now or always. "For this craft, we bias them away from zero speed" reads as a habit when it was a decision.
- Every sentence has a verb. A fragment is fine once as a beat; a list of noun-phrase sentences is not.
- Specific technical words and numbers beat generic value words. "A lot", "very", "really", "somehow", "something", "things", "stuff", "the trouble", "hurts", "worse", "better", "matters", "isn't quite" stand where a quantity or a mechanism belongs: say how much, or what happens ("the lag grows to ninety degrees", not "the delay hurts").
- `scripts/script_lint.py` checks these with spaCy (`fragment`, `fragment-ok?`, `tense-shift`, `vague-ref`) and a word list (`generic`). All are advisory prompts to listen to; a few false hits are normal (the small model mis-tags some verbs). It needs the Nix shell, or `pip install spacy && python3 -m spacy download en_core_web_sm`; without spaCy it prints one NOTE line and skips the grammar checks.

## 5. Numbers: results and meaning, not arithmetic

- Introduce a number with its quantity, unit and consequence. Repeat it when a comparison needs it, and keep baseline values distinct from changed cases. "A tenth of a degree, which from 500 kilometers up is almost a kilometer on the ground."
- Never read arithmetic aloud ("six thousand three hundred seventy eight point one four plus four hundred..."). The screen shows the working; the voice says what came out and why it has that shape.
- Every number spoken is either used again or makes a size concrete. Check `script_lint.py` (numbers per minute).
- Numbers must agree everywhere: if 0.1 s of delay is "about 14 degrees" in one scene, it is not "unknown" in another.

## 6. Pacing and breathing room

- One idea per paragraph. A blank line between paragraphs is a breath (the voice takes a longer pause).
- After a key result or a surprising picture, give the viewer 1 to 2 s of silence while it moves on screen: `[PAUSE 1.5]`. Silence while the picture works is pacing, not dead air.
- Plan on about 145 to 160 words a minute, then measure the real voice and add explicit holds where the picture needs time. Judge pacing by whether the viewer can follow the changing picture, not by the count.
- Recall pauses with a countdown ("flashcards") only when the user asks for them. By default the core idea comes back in different forms (on the system, in a picture, as an equation) without quizzing the viewer.
- Length: one story arc per video, about 8 to 12 minutes. When a topic has two arcs (for example the loop and sample rate, then jitter and isolation), make two videos rather than one long one.

## 7. The script reads well on the page too

The user reads scripts before they are voiced. Format `narration.txt` so it is easy to review:
- one paragraph per beat, at most about 4 sentences, blank line between paragraphs;
- `## Sxx Title` where the title is the question the scene answers ("Why can't the controller just push harder?"), not a label ("Bandwidth");
- `# ` comment lines for the screen action, kept short, so a reader sees what is shown while it is said;
- numbers written as the voice should say them, but nothing else that hurts reading.

## 8. Visuals show the real mechanism

"Oversimplified" was the user's complaint about visuals, not "not 3D enough". Visual depth does not follow from good prose; plan it. For each explanatory beat, write down the physical thing shown, what visibly changes, and the inference the viewer should make, then check the drawing supports that inference. A detailed spacecraft that explains nothing is no better than a ball on a spring.

- Draw the real thing the narration is about: the actual load path (wheel torque into the bus, through the root fitting, into the boom, back into the bus, to the tracker), the actual mode shape (with its node, when the mode has one), the actual Bode plot with the mode's spike and the loop's crossover, the actual sampled signal. Not a ball on a spring standing in for all of it.
- The picture should let an engineer check a number against it: a measured lag on a time trace, a crossover on a labelled axis, an angle on the drawn craft.
- Default to clean 2D: a cutaway or side view of the real hardware, plots, timing diagrams. Use 3D when orientation or depth is the point: a craft turning about its axes, a reaction wheel spinning one way while the bus turns the other, pointing geometry, orbit planes, a mode that twists. Those are hard to read in 2D. A realistic render that just sits there is not worth its render time.
- Motion must be smooth: compute shapes per frame in manim (a beam's deflection from its mode shape, a craft's rotation from a ValueTracker) rather than stepping through a small library of pre-rendered poses. Render motion-heavy scenes at 60 fps (`-qh` without `--frame_rate 30`).

## 9. Layout spacing

- One focal point per frame, and at most two groups (for example the craft on the left, its plot on the right). Everything else is gone.
- Keep at least 0.6 units of margin to the frame edge and about 0.5 units between separate groups. Crowded frames read as busy even when nothing overlaps.
- Labels at a readable size (`T(..., 24)` or larger at 1080p) and only the ones the narration says.
- When the narration moves on, the picture clears or transforms; do not keep adding to one diagram for minutes.

## 10. Technical model before prose

Before drafting, write short model notes: each input, output, sensor and actuator; what every plot's transfer function is (loop crossover is not closed-loop bandwidth); which values are derived and which are illustrative choices; and the limits of each formula. Check technical claims against these notes separately from the prose review. *Seen:* a rewrite said the star tracker holds the ground camera on target (it measures attitude), and treated a rise-time estimate as a demonstrated slew time.

## 11. Process

1. Write a one-page outline: the spine system, the core idea in one sentence, and the question chain (one line per beat, each beat the question the last one raised).
2. Write the opening through its first visible failure and explanation, with screen-action notes, voice it with the real TTS, and show the user both before extending the script. The voice is the hardest thing to fix later.
3. Write the full script. Run `python3 scripts/script_lint.py narration.txt` and clear every `CHECK` or justify it.
4. Read the script aloud (or have the voice model read a scene) and fix anything that sounds read rather than said.
5. Section S of `review-checklist.md` at Gate 1, by a fresh reviewer who gets this file.
6. Get the user's approval on the script before voicing or rendering anything.
