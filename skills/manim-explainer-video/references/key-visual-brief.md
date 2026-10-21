# Key-visual design brief: prompt template

Send this to the design subagent (the strongest model available). Fill in the brackets. Give file paths rather than pasting large files.

---

You are designing the key frames of a manim explainer video, in a 3Blue1Brown style with Tufte's data-ink principles. These stills will become the visual reference the whole video is animated from, so they must be right before anything moves.

Audience: [AUDIENCE].
Field: [FIELD]. Be as accurate as a [FIELD] expert would demand.

Read first:
- [path]/SKILL.md, sections "Visual principles" and "Hard rules from review". Every still must follow them.
- [path]/scripts/style.py (palette, `T()` for all text, `icon()`, helpers). Import it; don't restyle.
- [path]/references/creative-devices.md, especially "Anatomy and biology" if the topic is biological.
- Reference images or source figures: [paths, or "none: find accurate sources per creative-devices.md"].

Key beats to design:
[For each beat: id, absolute time range, narration excerpt, what the viewer must understand by the end of the beat.]

For each beat:
1. Propose 2 or 3 genuinely different approaches: a different representation, view or metaphor, not a color or layout tweak. At least one should be the field's standard textbook figure done well.
2. Build each as a small manim scene that subclasses `TL` from style.py, showing the beat's final composed state.
3. End the scene with `self.end()` and render a still with layout QA on: `QA=1 manim -s -ql --disable_caching <file>.py <Scene>`. Clear every line in `qa/<Scene>.txt`, then look at the PNG yourself. Fix anything that is inaccurate, cluttered, wobbly, clipped, or relies on caption text, then re-render. Only hand back stills you would defend to an expert.
4. manim writes the still to `media/images/<file>/<Scene>_ManimCE_v*.png`; copy it to `keyframes/<beat>/<option>.png` with its `.py` beside it.

Return a short list: per beat, each option's path and one line on what it shows and why it explains the idea. Name the option you would pick. Do not animate anything yet.
