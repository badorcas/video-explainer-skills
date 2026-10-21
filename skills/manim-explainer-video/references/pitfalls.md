# Pitfalls hit in production

Each entry is a real failure from a past video, with its fix. Skim this before a long run.

## Environment and disk
- **Disk full after installing the Blender shell.** The session disk is a fixed allowance; `df` showing 0 available with low "used" means the allowance is spent.
  - Fix: delete old projects' `media/`, `seg_*.mp4`, `partial_movie_files`, and unused Hugging Face models (`~/.cache/huggingface`, about 4 GB for an unused TTS). Deletes work even when writes fail.
  - Check `df` before pulling Blender (about 1 GB) or a TTS model (about 5 GB).
- **A tool call is capped at about 5 to 10 minutes.** Transcription, voice, alignment, full lint (more than 10 minutes for an 18-minute video) and HQ renders must run detached (`setsid nohup ... &`), then be polled. A background "wait for it" shell also has a time limit; when it is killed, the detached job usually finished anyway, so check its output before restarting anything.
- **`pkill -f` with a pattern that matches your own command kills your shell** (exit 144). Kill by PID.

## Voice (self-voiced narration)
- **Concurrent renders slow the local TTS 10 to 15×** through torch thread oversubscription.
  - Fix: hold the render lock for the whole voice job, renice the voice to -10, and stop (SIGSTOP, then kill) renders that started anyway.
- **Bad takes:** gibberish, an extra invented clause, a hallucinated prefix. They show up as `LOW` lines in `voicecheck.txt`.
  - Re-voice only those paragraphs with `voice.py --redo ID`, then re-run `align.py`.
  - Some lines need two or three redos.
- **Whisper hallucinates speech in silent pauses during alignment** (for example a phrase from the previous question appearing in the countdown pause). Before you redo a `LOW` line, transcribe that paragraph's wav on its own: if it is clean, the take is fine. Then anchor scene beats on words after the pause.
- **Homophones in voicecheck** ("short weight" for "short wait", digits against spelled-out numbers) are not errors.

## Script wording
- **Present tense for a past design choice.** "For this design, we bias the valves fully open." reads as a habit and makes the listener ask when. Say "we biased them" or "we have biased them". `script_lint.py` flags it as `tense-shift`.
- **Bare It/That at sentence start.** "That's roughly a seventh of the whole vehicle." and "It adds more time." leave the listener hunting for the referent. Name it: "The fuel is roughly a seventh...", "The second filter adds more time." `script_lint.py` flags it as `vague-ref`.

## Timing
- **The real voice is faster than the provisional word-count timeline.** Scenes built on the provisional timeline then reach cues late and overrun slots.
  - Fix: after the real voice lands, re-render everything.
  - Read `qa/<Scene>.late.txt`.
  - Make fixed-length animations budget against the real phrase gaps.
  - End scenes with `self.close()`.
- **Slot overrun from the closing fade.** A 0.05 s margin still overran by 0.19 s; use about 0.3 s, or `close()`.
- **Two phrases 0.7 s apart cannot hold a 1.7 s fade-out plus fade-in.** Start the transition before the first phrase, or cross-fade.

## Manim
- **`set_opacity` on an open curve fills it.** Use `set_stroke(opacity=...)` for lines.
- **`set_opacity` on a transparent PNG `ImageMobject` turns it into an opaque box.** Fade images with `FadeIn`/`FadeOut`, or swap pixel arrays.
- **Updaters freeze during `self.wait()`** in some cases; wait with an empty animation or animate the tracker across the wait.
- **Swapping the child images of a group leaves two copies on screen.** Keep one `ImageMobject` and replace its `pixel_array`.
- **An arc path with a large angle sends a moving object out of the frame.** Check the arc at the extreme (0.7π flew off the top; 0.22π stayed in frame).

## Agents and review
- **Scene agents report frames as fine without having opened them.** Their reports list which sheets they viewed; open the ones they didn't.
- **Agents waive lint checks too readily** ("lopsided" waived as intentional). The independent reviewer rejected most of those waivers; treat a waiver as a claim to verify.
- **Parallel agents drift on shared choices:** the same part drawn as a gear in one scene and a disk in another; the same delay in blue, then violet. Send a SHARED DECISIONS block with every fix round.
- **One agent's better asset doesn't reach the others** unless the supervisor tells them (a stronger bend library rendered by one part agent).
- **A reviewer can propose a fix that contradicts an approved still** (a sign convention). The approved still wins; check before passing a fix on.
- **Lint run from another directory writes its own `lint/`** instead of updating the scene folder's `lint/`. Run it from the scene folder.

## Git
- **Pushes are rejected because others push to the same branch.** Fetch and integrate first: `git fetch origin main && git merge --no-edit origin/main && git push origin HEAD:main`. Prefer merge over rebase when the branch history has merges you must keep (a subtree merge, for example).
- **A commit hook that demands commits of untracked files will pick up logs and media.** Gitignore render scratch (`media/`, `*.log`, frame libraries, sheets) at the start of a video, not after.
- **Never commit a half-written mp4.** Verify with `ffprobe` first, then `git add -f`.

## Security
- **Do not read or use cloud credentials found in the environment** (for TTS or anything else). Use local models, or credentials the user handed you for that purpose.
