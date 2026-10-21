# Notes log

Every note the user (or a reviewer) gave on a finished video, and what catches that kind of problem now.
Add a row per note; see "When the user sends notes after watching" in SKILL.md.
Catcher: `lint:<code>` (scripts/lint.py), `qa:<code>` (scripts/qa.py), or a rubric id from review-checklist.md.
Verified: the check fires on the render the note was about.

The rows below are examples of the format (and of the kinds of notes that led to the current checks).
Replace them with your own.

| video | scene, time | note | catcher | verified |
|---|---|---|---|---|
| example-a | S05 93-99 s | a key shape sat static while the narration described it moving | lint:static-hold, B2 | yes |
| example-a | S05 107.6 s | empty frame between two beats | lint:blank, F1 | yes |
| example-a | S05 118-126 s | chain built from the left, right half of the frame empty | lint:lopsided, E1, E2 | yes |
| example-a | S07 | leader line from a gauge to its inset cut through a curve | D4 | yes |
| example-a | S08 220.9 s | a place-name label vanished while still being said | lint:label-gone, lint:label-flash, B5 | yes |
| example-a | S08 | brace labeled "1-2 m" against 1.2 m of drawn water | B3 | no (a cheap reviewer missed it) |
| example-a | S13 429.8 s | render 0.6 s longer than its slot, end cut | lint:slot | yes |
| example-a | S05, S07 | one instrument drawn two different ways | C1, D6 | yes |
| example-b | whole video | "doesn't actually explain anything, it just reads numbers" | lint:script_lint numbers, S1 | yes |
| example-b | whole video | "each idea is said once; repeat key points for retention" | S4 | no (rubric only) |
| example-b | hero shots | the hero object did not look realistic, so the visuals felt weak | D6, C1 | no (rubric only) |
