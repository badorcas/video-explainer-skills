# Third-party notices

## Bundled

| Component | Where | License |
|---|---|---|
| Phosphor Icons (fill weight SVGs) | `skills/manim-explainer-video/assets/icons/` | MIT, full text in `assets/icons/LICENSE-phosphor.txt` |

## Fetched at run time, not bundled

These are downloaded by the Nix flake or by `voice.py` on first use and are not part of this repository.

| Component | Fetched by | License |
|---|---|---|
| faster-whisper `base.en` weights (Systran) | `flake.nix`, pinned and hash-checked | MIT |
| VibeVoice-1.5B weights (Microsoft) | `scripts/voice.py`, from Hugging Face | MIT |
| Caladea and DejaVu fonts | `flake.nix`, from nixpkgs | OFL 1.1 and the Bitstream Vera / DejaVu license |
| manim, ffmpeg, TeX Live, spaCy, Blender | `flake.nix`, from nixpkgs | their own licenses |
