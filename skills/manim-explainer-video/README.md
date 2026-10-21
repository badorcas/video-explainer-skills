# manim-explainer-video

A Claude skill and reproducible toolchain for turning narration audio (or a script) into a synced manim explainer video, in a 3Blue1Brown / Marshall Bruner style with Tufte's data-ink principles.

- `SKILL.md`: the workflow and visual principles (what Claude reads)
- `references/`: script writing, creative devices (3D, morphs, icons, Blender), the key-visual brief, the expert-review prompt, the yes/no frame-review checklist, pitfalls and a notes-log template
- `assets/icons/`: Phosphor fill icons (MIT), loaded with `icon()` from `style.py`
- `flake.nix`: pinned environment (manim, TeX, ffmpeg, faster-whisper with pinned weights, fonts); `#blender` adds Blender

Scripts (`scripts/`):

| Script | What it does |
|---|---|
| `style.py` | Palette, `T()` text, `icon()`, timing helpers (`TL`, `till`, `close`), countdown ring |
| `transcribe.py` | Timestamped transcript with faster-whisper |
| `voice.py` | Optional self-voiced narration with VibeVoice-1.5B (own venv) |
| `align.py` | Word timings (`words.json`) and a LOW-confidence report for a voiced script |
| `timing.py` | Beat times looked up from the script's words |
| `retime.py` | Move hard-coded beat times after a re-voice |
| `script_lint.py` | Flags script sentences that read numbers instead of explaining |
| `lint.py`, `qa.py`, `lq.sh` | Timing/composition lint; 480p15 renders with layout QA (overlaps, off-frame, clutter) |
| `grab.py` | Contact sheet of frames at chosen times, for review |
| `render_all.sh`, `hq_job.sh` | 1080p30 renders (a list of file:Scene specs, or named scenes of one file) |
| `assemble.py` | Fit each scene render to its slot, concatenate, mux the narration |
| `splice.py` | Frame-exact splice of insert clips (predict, recall, quiz) into a finished video |
| `blender_lineart.py`, `blender_stills.sh`, `contact_sheet.py` | Optional Blender line-art stills and a contact sheet |
| `setup.sh` | Apt-based setup for a container without Nix |

```bash
nix develop                                   # interactive shell
nix run .#transcribe -- narration.mp3 out/    # timestamped transcript
nix develop .#blender                         # optional, for 3D stills
```
