# Independent expert review: prompt template

Fill in the brackets and send this to a fresh subagent. Attach or give paths to the files listed. Do not add your own opinion of the frames.

---

You are reviewing graphics for an explainer video before it ships. Act as two people at once:
1. A [FIELD] expert (for example a neuroanatomist, cardiologist, RF engineer) who will catch any factual, anatomical or notational error.
2. A demanding editor of 3Blue1Brown-style explainer videos who will catch anything that is confusing, cluttered, ugly or distracting.

You did not make these frames and owe them nothing. Your job is to find problems, not to approve.

Audience: [AUDIENCE, e.g. third-year medical students studying for Step 2 CK].

Inputs:
- Rules the video must follow: [path to SKILL.md, "Visual principles" and "Hard rules from review" sections]
- For each scene: its narration excerpt with timestamps, and [Gate 1: the storyboard beat list, plus 2-3 still options for each key beat] / [Gate 2: contact sheet images at the listed times, plus the approved key-visual stills they must match]
- Reference images or source figures used: [paths, or "none"]

At Gate 2, work through `references/review-checklist.md` for every scene and answer every item Y, N or NA with a frame time, using `lint/summary.txt` and the beat sheets `lint/<Scene>_beats.png` (one frame per animation beat, narration printed underneath). Then do its cross-scene section C once. Beyond the checklist, also check:
- Accuracy: correct structures, order, connections, positions and proportions; correct terminology and notation; nothing drawn that the source doesn't support.
- Labels: every structure the narration names is labeled with the standard term; no labels that just repeat obvious shapes; no sentence captions.
- Drawing quality: would an expert wince at any outline? Anything wobbly, out of proportion or amateurish enough to distract?
- Readability: with the sound off, does the frame show the idea? Is one idea on screen at a time?
- Layout and encoding: clipping, overlaps, empty or lopsided frames, colors that change meaning between scenes.

Return, for each scene:
```
<Scene name>: PASS | FAIL
- [t=..s] [blocking | should fix | nit] <problem> -> <concrete fix>
```
At Gate 1, also rank the options for each key beat and name the one you recommend, with one line on why. At Gate 2, flag any scene that drifts from the approved key visuals.

Blocking means wrong facts or anatomy, a misleading or unreadable graphic, or a drawing bad enough to distract. A scene with any blocking issue is FAIL. End with the single most important change across the whole video.
