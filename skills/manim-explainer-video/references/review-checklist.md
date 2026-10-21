# Review rubric (section S at Gate 1, the rest at Gate 2)

A checklist a reviewer of any strength can follow. Each item is a yes/no question with a fixed way
to check it. "Looks fine" is not an answer: every item gets Y, N or NA, and every N becomes an issue
with the severity listed. The items come from defects that real reviews caught in finished scenes.

## Inputs
- `lint/summary.txt` and `lint/<Scene>_beats.png` (and `_beats2.png`, ...) from
  `python3 lint.py <transcript.json> --host=intercut.py --sheets file:Scene ...`. A beat sheet has the settled frame of
  every animation beat and a frame every ~3 s inside long animations (captioned "moving"), each with the narration
  said during it printed underneath. `WAIVED` lines give the author's reason: judge the reason. `HOST` lines are
  covered by the host on camera: skip them.
- The storyboard (scene table and its **Encoding** section: what each color and marker means).
- The approved key-visual stills (`keyframes/approved/`), and the source figures if any.
- For any detail you can't see at 480p, grab a full-size frame: `python3 grab.py <Scene> <seconds into scene>`.

## S. Script (Gate 1, before voicing; skip when the narration is a recording you were given)
Read `references/script-writing.md`, then run `python3 scripts/script_lint.py narration.txt` and read every `CHECK`.
- **S1** Every explanatory sequence explains a mechanism, not just a result, and its causal claims are correct against the model notes (`script-writing.md` section 10; a wrong causal claim is blocking). For each scene write the one-sentence "why" a
  viewer could repeat without the numbers ("light is a wave, so a finite opening blurs every point into a disk,
  and a wider opening blurs less"). If the scene only lets you write a number or a formula, it is N. Before a
  formula is used, the narration has shown why it has that shape (what grows, what shrinks, and why).
  (blocking)
  *Seen:* a worked-problem video derived five design quantities as one number per sentence; the viewer
  said it "doesn't actually explain anything, it just blabs numbers".
- **S2** One concrete system is the spine, and the idea is still general. The same named system (with its
  numbers) runs from the first minute to the end; analogies appear for a sentence or two and the narration
  returns to the real hardware. Each scene also states its general rule in one sentence after the example
  forced it. Check: strike the system's name and look for that sentence in each scene. A middle that teaches
  how to present the answer instead of the mechanism is still N. (blocking if a scene has no general
  rule, or the system is replaced by a metaphor for more than a paragraph; otherwise should fix). A reduced
  model is fine when its parts stay visibly mapped to the hardware; the general rule need not be repeated in
  every scene, only in each major explanation.
  *Seen:* a worked-problem video "weirdly overfit" to its one problem; a vibration video that dropped its
  real machine at 1:05 for a spring and a swing, which the user called "too oversimplified".
- **S3** Numbers are rationed: every `numbers` or `arith` CHECK has been reviewed in context (a derivation or
  comparison the lesson needs is fine),
  every number spoken is either used again or makes a size concrete, and each number agrees with every other
  mention of it. (should fix; blocking if two scenes contradict)
- **S4** The core idea comes back, spaced and in different forms. Write the video's one-sentence core idea.
  It develops through prediction, evidence and application, and comes back when a new form (on the system, a
  picture, the equation) or a new consequence adds understanding. Recall pauses with a countdown only if the
  user asked for them. (should fix)
- **S5** Story order: each scene answers a question the previous one raised, or supplies a clearly needed
  prerequisite, and the sequence resolves the opening problem. Major ideas are met as problems before they
  are named. No term, rule or classification arrives before the viewer knows what it is for. Each scene's title is
  the question it answers, and the previous scene raised that question. (blocking)
  *Seen:* a script that sorted "three frequencies" into structure, control and hardware before showing why
  anyone should care; the user said it had no story.
- **S6** List the unfamiliar terms the reasoning needs and where each becomes understandable. Each arrives
  when needed, and a phrase that leaves a listener asking "of what?" is resolved right there. A glossary that
  interrupts the active question is N. (should fix)
- **S7** It sounds said, not read. Treat each style CHECK from `script_lint.py` as a pointer, then listen to
  the opening and the densest passage in the real TTS voice: no slogan runs ("Same motor. Same command.
  Opposite motion."), no sentences padded or comma-joined to pass the lint, no forced questions or filler. (blocking if more than a third of scenes fail)
  *Seen:* two scripts at about 10 words a sentence that the user said "don't feel like they're written by a
  human".
- **S8** It reads well on the page and breathes: paragraphs of one idea under about 90 words with a blank
  line between them, explicit holds long enough to read each important visual change, and one story arc per video (about 8 to 12
  minutes; split a second arc into its own video). (should fix)
- **S9** Grammar of the spoken line: no bare It/That/This/These/Those opening a sentence before a verb (`vague-ref`); a past design choice is not in present simple (`tense-shift`); every sentence has a verb (`fragment`); no generic value words where a number or mechanism belongs (`generic`). Walk each such CHECK from `script_lint.py` and fix or accept it with a reason. (should fix; blocking if a scene's key claim hangs on a bare "That")
  *Seen:* "For this design, we bias the valves fully open." (a decision stated as a habit); "That's roughly a seventh of the whole vehicle" with no named thing.

## A. Lint lines (do these first)
For each line in `lint/<Scene>.txt`, open the frame at its time and decide.
- **A1** Every `ERROR` is fixed. (blocking if a label vanishes mid-word or the slot is wrong; otherwise should fix)
- **A2** Each `CHECK` is either fixed or justified in one sentence you would accept from someone else. For
  `static-hold`, read the printed narration: if it names things (a list, a place, an object) that do not
  light up as they are said, it is N. (should fix)

## B. Narration against picture: go through the beat sheet frame by frame
- **B1** The main thing the narration names in this beat is visible in this frame or the next one. (blocking if it
  is the scene's key idea; else should fix)
- **B2** When the narration describes motion or change ("travels", "splits", "grows", "fades", "passes",
  "drifts"), two consecutive beat frames differ in exactly that way. A shape that just sits there while the
  narration says it moves is N. (should fix)
  *Seen:* an uplifted sea surface sat as a static plateau for 15 s while the narration said "giant wave".
- **B3** Every number or size claim on screen matches the narration and the drawing. Measure it: a brace
  labeled "1-2 m" must span 1-2 m of the drawn scale. (blocking if it contradicts; nit if only loose)
- **B4** When the narration lists items ("streets, traffic, homes, boats, docks"), each one is shown or
  highlighted in the same order, near the moment it is said. (should fix)
- **B5** A label the narration says stays up until about 1 s after the word ends (lint `label-gone`). (should fix)

## C. Consistency across scenes (once per video)
Make a short table: each recurring object or process, and the scenes it appears in. Put those
frames side by side.
- **C1** The same object is drawn the same way in every scene: same icon, same glyph, same color.
  *Seen:* a buoy drawn two different ways; a tide gauge drawn as a wave icon in one scene and as the map's
  inverted triangle in another. (should fix)
- **C2** The same physical process has the same shape and sign in every scene. Compare the frames directly.
  *Seen:* one scene showed the forced wave as a pure dip under the pressure, while two others showed a crest
  ahead and a trough under it. (blocking: it teaches two different things)
- **C3** Each color keeps the one meaning given in the storyboard's Encoding section. Check every colored
  element in the beat sheets against that list. (should fix)
- **C4** A key-beat scene lands on its approved still (same layout, same representation). (should fix)

## D. Drawing correctness (look at full-size frames)
- **D1** Every fill (water, ground, a band) ends at the frame edge or at a physical boundary (shore, wall, seabed).
  A free-standing vertical edge in mid-frame is N. *Seen:* harbor water ending in a cliff short of the frame edge;
  water ending as a vertical wall at the beach. (should fix)
- **D2** Things behave physically: floating objects ride the surface, water doesn't pass through solid walls,
  objects don't sink into the ground. (blocking if it teaches the wrong physics; else should fix)
- **D3** Each label sits right next to what it names, on the outside, not floating in the middle of nowhere.
  An axis label sits at the end of its axis. *Seen:* a time-axis "t" placed 0.6 units below its axis. (should fix)
- **D4** Leader and connector lines run through empty space. One that cuts across a curve or another label is N.
  *Seen:* a dashed leader from a gauge to its inset cutting through the pressure curve. (should fix)
- **D5** Several sources feeding one target use drops into a bus with one arrow out, and arrows land on a box
  edge. One arrow from the middle of a row, or a row hanging off one end of the chain, is N. (should fix)
- **D6** With the sound off, each icon reads as what it is meant to be. If you would have to guess (a buoy
  that looks like a joystick, an ambiguous "broadcast" glyph), it is N: use the standard glyph or add a
  one-word label. (should fix)
- **D7** Objects drawn "to scale" have true proportions (a car about 1.5 m tall, a door about 2 m, a person
  1.75 m). (should fix)
- **D8** When two panels show the same event (a sloshing basin and its response curve, a map and its time
  series), something visible ties them: a shared color, a marker that moves or pulses in step, or a
  connector. Two side-by-side panels with no link is N. *Seen:* a sloshing harbor next to its resonance
  curve, with nothing marking that the harbor sits at the peak. (should fix)
- **D9** The scene's last picture shows the thing the narration ends on, with the same glyph the video
  used for it before. *Seen:* a warning chain ending on a generic people icon while the narration said
  "the signs", which S02 had drawn as the actual evacuation sign. (should fix)

- **D10** When a hero object (a vehicle, a machine, an instrument) is shown, it is drawn accurately (a clean 2D cutaway of the real parts is fine; 3D only when depth is the point), not an icon. In hero shots it fills at least 35% of the frame width. Its motion (a turn, a bend, ringing) is plainly visible at playback size. A flexible part that swings as a straight rod on a hinge is N. *Seen:* a boom drawn as a rigid rod with straight ghosts while the narration said "bends"; a realistic model at 17% of the width in a corner. (should fix; blocking if the motion is the point of the scene)
- **D11** Overlays tied to a moving object start at the right part and move with it. *Seen:* a camera line of sight drawn from the engine nozzle, staying vertical while the narration said "the camera tilts with it". (should fix)
- **D12** Every response or gain plot names its y quantity ("|L|", "|S|") and has decade labels on log axes. The reference line is labelled ("1" on unity). Illustrative curves get a small "schematic" tag. A label that contradicts the curve beside it (|L|<1 shown over a spike above 1) is blocking. (should fix)
- **D14** The picture shows the real mechanism the narration explains (the load path, the mode shape with its node, the measured lag on a trace), detailed enough that an engineer could check a number against it. A metaphor object standing in for the system for more than a sentence or two is N. (should fix)
- **D15** Motion is smooth at playback: no visible stepping between poses. Motion is computed per frame, and motion-heavy scenes render at 60 fps. (should fix)
- **D13** "Faster", "bigger" and "longer" comparisons show the change, with a distinct value in each panel. *Seen:* three "shake slower / faster / faster again" panels all drawn at the same frequency. (blocking)

## E. Layout
- **E1** The composition is centred, or deliberately split into columns. No half of the frame stays empty
  for 5 s or more (lint `lopsided`). (should fix)
- **E2** A row of items that builds one at a time stays centred as it grows; it is not left-justified. (should fix)
- **E3** No text-only stretch of 3 s or more, and most frames have under five words that aren't math
  (lint `text-only`, `wordy`). (nit, or should fix if it lasts)

## F. Transitions and pacing
- **F1** No empty frame inside a scene for 0.8 s or more (lint `blank`). (nit)
- **F2** When the next scene starts from the same picture, it is a straight cut, not a fade-out and fade-in
  (lint `fade-flicker`). (should fix)
- **F3** When the narration changes topic, the picture changes within about 2 s. A frame identical to the
  previous scene's end for 10+ s is N. (should fix)

## G. Facts
- **G1** Every number on screen appears in the source paper or the narration. Write down where (page, table or
  figure) for each. (blocking if one doesn't)
- **G2** Anything illustrative rather than from data is tagged small and dim ("schematic"). (should fix)
- **G3** Terms and notation are the field's standard ones. (blocking if wrong)

## Output
For each scene:
```
<Scene>: PASS | FAIL
A1 Y | A2 N 221.0 (list not highlighted) | B1 Y | B2 Y | B3 N 211.2 | B4 N 221-227 | B5 Y | D1 Y | ... | G2 Y
- [t=..s] [blocking | should fix | nit] <problem> -> <concrete fix>
```
Then section C once for the whole video, with its table. A scene with any blocking N is FAIL.

## Who runs which part
Sections A, B, D, E and F are mechanical with the lint output and beat sheets, so a cheaper model can do
the per-scene pass. Sections C and G need the whole video and the paper in view: give those to the strongest
reviewer available, or do them yourself, at Gate 2 and on any re-review that changes shapes or numbers.
