---
name: brag-claudemy
description: Make a short product video, about 25 to 30 seconds, from a brief, a spec or a real product, using the founder's own method from the Claudemy videos. It writes the brief and rulings first, measures a reference video for pace, designs and storyboards every scene with a source tag on every line, builds a rendered-frame page (or generated shots, or Hyperframes beats), makes a calm soundtrack, renders, and then runs a verifier that checks loudness, pace, copy rules, sources and the poster frame. It never spends money without an approved line and never shows a concept as if it were working software. Use when someone asks for a measured, source-tagged or concept-labelled product video, says "the Claudemy method", "brag-claudemy", or "build a video from this spec", or wants pace measured against a reference. For a quick one-command launch video of a built project, the plain brag skill is the lighter choice.
license: MIT
---

# brag-claudemy (the founder's product video method)

This is the Claudemy method, bundled. The two Claudemy videos are the worked examples (references/method.md): the app tour built from Hyperframes beats on 2026-10-15, and the Sonos cut built from generated shots, real UI and measured pace on 2026-10-23. The method is a sequence of gates, each with a file and a check. The checks are scripts, so they do not depend on you remembering them.

Scripts live in this skill's `scripts/` folder (the base directory shown when the skill loads). Call them by absolute path. Read `references/rulings.md` first: the founder's rulings override anything else.

## Inputs
- A brief in words, a spec file, or a live product URL. Ask only for what is missing.
- Whether the product is built (STATUS: BUILT) or a concept (STATUS: CONCEPT). If unsure, it is CONCEPT. Read `references/claims.md`.

## Before starting
Check and say in one line what is missing: `ffmpeg`, `ffprobe`, `python3` with `numpy`, `uv`, Google Chrome installed. Rendering needs `uv run --with playwright`; tracking needs `uv run --with opencv-python-headless --with numpy`.

## Workflow

1. **Scaffold.** `bash <skill>/scripts/scaffold.sh <project-dir> "<Name>" concept|built`. It creates BRIEF.md, rulings.md, rulings.json, DESIGN.md, STORYBOARD.md, SCRIPT.md, reference.json, audio-plan.json and index.html. Work inside the project folder from now on. Never run this skill inside a folder that holds client data, credentials or a private repo: build in a clean folder and copy in only what the video needs.

2. **Brief.** Fill BRIEF.md with the user. Add forbidden words (client names, confidential material) to rulings.json. If the user gives a ruling at any point, append it to rulings.md (and rulings.json if a script can check it) in that same turn, before acting on it.

3. **Reference.** Ask for a reference video. If a local clip exists, run `python3 <skill>/scripts/pace.py <reference.mp4> --json` and write the targets into reference.json. If not, keep the template (Sonos, measured 2026-10-23) and say so. The done-means is these numbers, set before building.

4. **Design.** DESIGN.md. BUILT: from the real product's captured design. CONCEPT: a proposal; the founder picks. Say what the look is not.

5. **Storyboard and script.** STORYBOARD.md (about 5 scenes of 4 to 6 seconds, a small chapter label each, one idea per scene) and SCRIPT.md. Every line under "## On-screen text" ends with `[src: id]`. If a line has no source, it does not go on screen. Show both files to the user and get the go-ahead before building.

6. **Choose the route and say it.** Name the options and mark the pick:
   - R1 page (default, no spend): `references/route-page.md`.
   - R2 generated shots with motion, real UI composited: `references/route-generated.md`. Costs money; needs the spend gate.
   - R3 Hyperframes beats: `references/route-beats.md`.
   Read `references/spend-gate.md` before anything that costs money. No approved line in BRIEF.md "Spend approved", no spend.

7. **Build.** Follow the route file. Render stills first and look at every one. Fix what you see before the full render. Then `python3 <skill>/scripts/audio.py audio-plan.json` and `bash <skill>/scripts/mux.sh frames soundtrack.wav renders/<name>.mp4 <poster-seconds>`.

8. **Verify.** `python3 <skill>/scripts/verify.py renders/<name>.mp4 --project .`. Fix every FAIL. Re-measure after each round and compare to the reference, not to the last attempt. At most three rounds on one class of fix; if the same failure happens twice, stop and diagnose before a third try. Then report.

9. **Share copy.** Write it in SCRIPT.md under "Share copy". Short, plain, no claim without a source tag. Add any music credit line.

## Done means
- verify.py prints no FAIL, and its "not verified" list is reported to the user as it is.
- The founder has seen the video, not only the numbers.
- Spend, if any, is logged in plan.md against the approved line.

## Final report (short)
Files and paths, the verify.py output verbatim, what was not verified, spend, rulings added this session, and the one next step.

## Hard rules
- No emdashes, no double hyphens in visible text; `scripts/copylint.py` runs inside verify.py.
- No narration, no invented voices or quotes. Voices are the product's own real output only.
- Concept mode: label on every scene, invented data only, no prices, customers, or numbers about speed or accuracy.
- Never print, copy or commit a key.
- Nothing is published or posted by this skill.
