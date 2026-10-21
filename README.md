# Claude skills

Skills for [Claude Code](https://claude.com/claude-code) and other Claude agents that load `SKILL.md` skills.

| Skill | What it does |
|---|---|
| [`manim-explainer-video`](skills/manim-explainer-video/) | Turns narration audio (a podcast, lecture or voiceover) or a script into a synced manim explainer video in a 3Blue1Brown style with Tufte's data-ink principles. It covers script writing, optional local text-to-speech, word alignment, a style kit, layout and timing lint, frame review gates, rendering, assembly and frame-exact inserts. |

## Install

A skill is a folder with a `SKILL.md` at its root. Copy or symlink it into your skills directory:

```bash
git clone <this repo> claude-skills
mkdir -p ~/.claude/skills

# symlink (updates with git pull)
ln -s "$PWD/claude-skills/skills/manim-explainer-video" ~/.claude/skills/manim-explainer-video

# or copy
cp -r claude-skills/skills/manim-explainer-video ~/.claude/skills/
```

For one project only, use `<project>/.claude/skills/` instead of `~/.claude/skills/`. Claude picks the skill up when a request matches its description (for example "make a manim explainer for this mp3").

## Quick start with Nix

The skill ships a flake that pins manim, a minimal TeX, ffmpeg, faster-whisper (weights fetched and hash-checked on first use) and the fonts, so renders look the same on every machine.

```bash
cd ~/.claude/skills/manim-explainer-video
nix develop                                       # shell with manim, TeX, ffmpeg, whisper
nix run .#transcribe -- narration.mp3 out/        # timestamped transcript
nix develop .#blender                             # optional, adds Blender for 3D stills
```

Flakes need `experimental-features = nix-command flakes` in `~/.config/nix/nix.conf`. Without Nix, `scripts/setup.sh` installs the same tools with apt on Debian or Ubuntu.

Optional narration with VibeVoice-1.5B runs from its own Python venv; `SKILL.md` has the setup.

## Layout

```
skills/manim-explainer-video/
  SKILL.md        workflow and visual principles
  references/     script writing, review checklist, pitfalls, creative devices, prompts
  scripts/        style kit, lint and QA, voice, alignment, timing, render, assemble, splice
  assets/icons/   Phosphor icons (MIT)
  flake.nix       pinned environment
```

## License

MIT, see [LICENSE](LICENSE). Bundled third-party assets are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
